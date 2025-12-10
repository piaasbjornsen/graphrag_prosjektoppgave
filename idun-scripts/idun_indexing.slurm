#!/bin/bash
#SBATCH --job-name=graphrag_index
#SBATCH --partition=GPUQ
#SBATCH --account=share-ie-idi
#SBATCH --time=2-00:00:00          # 2 days - for large datasets like novel.json
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G                  # 32GB RAM - increase for larger datasets
#SBATCH --gres=gpu:1               # 1 GPU
#SBATCH --output=logs/graphrag_index_%j.out
#SBATCH --error=logs/graphrag_index_%j.err
#SBATCH --mail-user=<ntnu-username>@stud.ntnu.no
#SBATCH --mail-type=ALL

# Exit on error, undefined variables, and pipe failures
set -euxo pipefail

echo "=========================================="
echo "GraphRAG Indexing Job on IDUN"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Started: $(date)"
echo "=========================================="

# Navigate to project directory
PROJECT_DIR=/cluster/work/$USER/graphrag-idun
cd "$PROJECT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Load required modules
echo "Loading modules..."
module purge
module load Python/3.12.3-GCCcore-13.3.0
module load ollama/0.6.0-GCCcore-13.3.0-CUDA-12.6.0

# Show loaded modules
echo "Loaded modules:"
module list || true

# Show Python and Ollama versions
echo "Python version:"
python --version || true
echo "Ollama version:"
ollama --version || true

# Show GPU info
echo "GPU info:"
nvidia-smi || true

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Verify GraphRAG installation
echo "GraphRAG version:"
python -c "import graphrag; print(graphrag.__version__)" || echo "GraphRAG not found!"

# Set up Ollama
echo "Setting up Ollama..."
export OLLAMA_MODELS=/cluster/work/$USER/.ollama_models
mkdir -p "$OLLAMA_MODELS"

# Bind Ollama to localhost
export OLLAMA_HOST=127.0.0.1:11434

# CRITICAL: Ollama parallelism settings
# NUM_PARALLEL must match concurrent_requests in settings.yaml
# P100-16GB can fit both models + 6 parallel KV caches (~13.3 GiB of 15.6 GiB)
export OLLAMA_NUM_PARALLEL=6
export OLLAMA_MAX_LOADED_MODELS=2  # Keep both LLM and embedding model loaded

# Start Ollama server in background
echo "Starting Ollama server..."
ollama serve > logs/ollama_serve_${SLURM_JOB_ID}.log 2>&1 &
OLLAMA_PID=$!
echo "Ollama PID: $OLLAMA_PID"

# Wait for Ollama to start
echo "Waiting for Ollama to initialize..."
sleep 10

# Check if Ollama is running
if ! kill -0 $OLLAMA_PID 2>/dev/null; then
    echo "ERROR: Ollama failed to start!"
    cat logs/ollama_serve_${SLURM_JOB_ID}.log
    exit 1
fi

# Pull required models if not already present
echo "Checking/pulling required models..."

# Chat model (adjust to your preferred model)
CHAT_MODEL="mistral:latest"  # Change to qwen2.5:14b or your preferred model
echo "Checking chat model: $CHAT_MODEL"
if ! ollama show "$CHAT_MODEL" >/dev/null 2>&1; then
    echo "Pulling $CHAT_MODEL..."
    ollama pull "$CHAT_MODEL"
else
    echo "$CHAT_MODEL already available"
fi

# Create a custom modelfile with increased context for entity extraction
echo "Creating custom Mistral configuration with larger context..."
cat > /tmp/Modelfile_mistral_large <<EOF
FROM mistral:latest
PARAMETER num_ctx 8192
PARAMETER temperature 0
EOF

# Create the custom model
echo "Loading custom model configuration..."
ollama create mistral-large -f /tmp/Modelfile_mistral_large 2>&1 || echo "Custom model already exists or created"
rm -f /tmp/Modelfile_mistral_large

# Embedding model (adjust to your preferred embedding model)
EMBEDDING_MODEL="nomic-embed-text"
echo "Checking embedding model: $EMBEDDING_MODEL"
if ! ollama show "$EMBEDDING_MODEL" >/dev/null 2>&1; then
    echo "Pulling $EMBEDDING_MODEL..."
    ollama pull "$EMBEDDING_MODEL"
else
    echo "$EMBEDDING_MODEL already available"
fi

# List available models
echo "Available Ollama models:"
ollama list

# Navigate to ragtest directory (or use root if you prefer)
cd ragtest

# Verify input files exist
echo "Input files:"
ls -lh input/ || echo "No input files found!"

# Run GraphRAG indexing
echo "=========================================="
echo "Starting GraphRAG indexing..."
echo "Start time: $(date)"
echo "=========================================="

python -m graphrag.index \
    --root . \
    --verbose

INDEX_EXIT_CODE=$?

echo "=========================================="
echo "Indexing completed with exit code: $INDEX_EXIT_CODE"
echo "End time: $(date)"
echo "=========================================="

# Check outputs
if [ $INDEX_EXIT_CODE -eq 0 ]; then
    echo "Indexing successful! Output files:"
    ls -lh output/*.parquet 2>/dev/null || echo "No parquet files found"
    
    echo "Vector store:"
    ls -lh output/lancedb/ 2>/dev/null || echo "No vector store found"
    
    echo "Cache files:"
    ls -lh cache/ 2>/dev/null || echo "No cache files"
    
    echo "Logs:"
    ls -lh logs/ 2>/dev/null || echo "No log files"
else
    echo "ERROR: Indexing failed with exit code $INDEX_EXIT_CODE"
    echo "Check logs for details:"
    echo "  - Job output: logs/graphrag_index_${SLURM_JOB_ID}.out"
    echo "  - Job errors: logs/graphrag_index_${SLURM_JOB_ID}.err"
    echo "  - Ollama log: logs/ollama_serve_${SLURM_JOB_ID}.log"
fi

# Clean up: kill Ollama server
echo "Cleaning up..."
kill $OLLAMA_PID || true
wait $OLLAMA_PID 2>/dev/null || true

echo "=========================================="
echo "Job finished: $(date)"
echo "=========================================="

exit $INDEX_EXIT_CODE


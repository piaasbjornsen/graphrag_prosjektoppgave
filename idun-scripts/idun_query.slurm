#!/bin/bash
#SBATCH --job-name=graphrag_query
#SBATCH --partition=GPUQ
#SBATCH --account=share-ie-idi
#SBATCH --time=0-00:30:00          # 30 minutes - usually enough for queries
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G                  # 16GB RAM - increase if needed
#SBATCH --gres=gpu:1               # 1 GPU
#SBATCH --output=logs/graphrag_query_%j.out
#SBATCH --error=logs/graphrag_query_%j.err
#SBATCH --mail-user=piaas@stud.ntnu.no
#SBATCH --mail-type=ALL

# Exit on error, undefined variables, and pipe failures
set -euxo pipefail

echo "=========================================="
echo "GraphRAG Query Job on IDUN"
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

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Set up Ollama
echo "Setting up Ollama..."
export OLLAMA_MODELS=/cluster/work/$USER/.ollama_models
export OLLAMA_HOST=127.0.0.1:11434

# Start Ollama server in background
echo "Starting Ollama server..."
ollama serve > logs/ollama_serve_query_${SLURM_JOB_ID}.log 2>&1 &
OLLAMA_PID=$!
echo "Ollama PID: $OLLAMA_PID"

# Wait for Ollama to start
echo "Waiting for Ollama to initialize..."
sleep 10

# Check if Ollama is running
if ! kill -0 $OLLAMA_PID 2>/dev/null; then
    echo "ERROR: Ollama failed to start!"
    cat logs/ollama_serve_query_${SLURM_JOB_ID}.log
    exit 1
fi

# Verify models are available (they should be from indexing)
echo "Available models:"
ollama list

# Navigate to ragtest directory
cd ragtest

# Verify indexed data exists
echo "Checking indexed data..."
if [ ! -d "output" ]; then
    echo "ERROR: No output directory found! Run indexing first."
    kill $OLLAMA_PID || true
    exit 1
fi

# Find the most recent output directory (GraphRAG creates timestamped directories)
LATEST_OUTPUT=$(ls -td output/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_OUTPUT" ]; then
    echo "ERROR: No indexed output directories found! Run indexing first."
    kill $OLLAMA_PID || true
    exit 1
fi

echo "Using indexed data from: $LATEST_OUTPUT"
if [ ! -d "${LATEST_OUTPUT}artifacts" ] || [ -z "$(ls -A ${LATEST_OUTPUT}artifacts/*.parquet 2>/dev/null)" ]; then
    echo "ERROR: No parquet files found in ${LATEST_OUTPUT}artifacts/"
    kill $OLLAMA_PID || true
    exit 1
fi

# ===========================================
# CONFIGURE YOUR QUERY HERE
# ===========================================

# Query settings
QUERY_METHOD="global"  # Options: only global due to graphrag-local-ollama
QUERY_TEXT="What are the main themes and topics discussed in the documents?"  # Change this to your question
COMMUNITY_LEVEL=2     # Leiden hierarchy level (0-N, higher = smaller communities)
RESPONSE_TYPE="Multiple Paragraphs"  # Or: "Single Sentence", "List of 3-7 Points", etc.

echo "=========================================="
echo "Query Configuration:"
echo "  Method: $QUERY_METHOD"
echo "  Question: $QUERY_TEXT"
echo "  Community Level: $COMMUNITY_LEVEL"
echo "  Response Type: $RESPONSE_TYPE"
echo "=========================================="

# Run GraphRAG query
echo "Running GraphRAG query..."
echo "Start time: $(date)"

python -m graphrag.query \
    --root . \
    --method "$QUERY_METHOD" \
    --community_level "$COMMUNITY_LEVEL" \
    --response_type "$RESPONSE_TYPE" \
    "$QUERY_TEXT"

QUERY_EXIT_CODE=$?

echo "=========================================="
echo "Query completed with exit code: $QUERY_EXIT_CODE"
echo "End time: $(date)"
echo "=========================================="

# Clean up: kill Ollama server
echo "Cleaning up..."
kill $OLLAMA_PID || true
wait $OLLAMA_PID 2>/dev/null || true

echo "=========================================="
echo "Job finished: $(date)"
echo "=========================================="

exit $QUERY_EXIT_CODE



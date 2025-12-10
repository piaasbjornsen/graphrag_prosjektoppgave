#!/bin/bash

# Setup script for GraphRAG on IDUN
# Run this once after extracting the package on IDUN

set -e

echo "=========================================="
echo "GraphRAG IDUN Environment Setup"
echo "=========================================="

# Check if we're on IDUN
if [[ ! "$HOSTNAME" =~ idun ]]; then
    echo "WARNING: This doesn't look like an IDUN node. Hostname: $HOSTNAME"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get current directory
PROJECT_DIR=$(pwd)
echo "Project directory: $PROJECT_DIR"

# Load required modules
echo ""
echo "Step 1: Loading required modules..."
module purge
module load Python/3.12.3-GCCcore-13.3.0
module load ollama/0.6.0-GCCcore-13.3.0-CUDA-12.6.0

# Show versions
echo "Python version: $(python --version)"
echo "Ollama version: $(ollama --version)"

# Create virtual environment
echo ""
echo "Step 2: Creating Python virtual environment..."
if [ -d ".venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf .venv
fi

python -m venv .venv
source .venv/bin/activate

# Upgrade pip and install build tools
echo ""
echo "Step 3: Upgrading pip and installing build tools..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo ""
echo "Step 4: Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Install GraphRAG package from source (editable mode)
echo ""
echo "Step 5: Installing GraphRAG package from source..."
if [ -d "graphrag" ] && [ -f "pyproject.toml" ]; then
    pip install -e .
else
    echo "ERROR: GraphRAG source code not found! Make sure graphrag/ directory and pyproject.toml exist."
    exit 1
fi

# Verify installation
echo ""
echo "Step 6: Verifying installation..."
python -c "import graphrag; print('GraphRAG successfully imported!')" || {
    echo "ERROR: GraphRAG installation verification failed!"
    exit 1
}

# Create necessary directories
echo ""
echo "Step 7: Creating necessary directories..."
mkdir -p ragtest/logs
mkdir -p ragtest/output
mkdir -p ragtest/cache
mkdir -p logs

# Set up Ollama models directory
echo ""
echo "Step 8: Setting up Ollama models directory..."
OLLAMA_MODELS_DIR=/cluster/work/$USER/.ollama_models
mkdir -p "$OLLAMA_MODELS_DIR"
echo "Ollama models will be stored in: $OLLAMA_MODELS_DIR"

# Create a module loading script
echo ""
echo "Step 9: Creating convenience scripts..."
cat > load_modules.sh << 'EOF'
#!/bin/bash
# Load required modules for GraphRAG
module purge
module load Python/3.12.3-GCCcore-13.3.0
module load ollama/0.6.0-GCCcore-13.3.0-CUDA-12.6.0
echo "Modules loaded for GraphRAG"
EOF
chmod +x load_modules.sh

# Create activation script
cat > activate_env.sh << 'EOF'
#!/bin/bash
# Activate GraphRAG environment
source load_modules.sh
source .venv/bin/activate
export OLLAMA_MODELS=/cluster/work/$USER/.ollama_models
export OLLAMA_HOST=127.0.0.1:11434
echo "GraphRAG environment activated"
echo "Python: $(which python)"
echo "GraphRAG version: $(python -c 'import graphrag; print(graphrag.__version__)')"
EOF
chmod +x activate_env.sh

# Summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. To activate the environment manually:"
echo "   source activate_env.sh"
echo ""
echo "2. Review and customize SLURM scripts:"
echo "   - idun-scripts/idun_indexing.slurm"
echo "   - idun-scripts/idun_query.slurm"
echo ""
echo "3. Verify your input files are in place:"
echo "   ls -lh ragtest/input/"
echo ""
echo "4. Submit indexing job:"
echo "   sbatch idun-scripts/idun_indexing.slurm"
echo ""
echo "5. Check job status:"
echo "   squeue -u \$USER"
echo ""
echo "6. After indexing completes, submit query job:"
echo "   sbatch idun-scripts/idun_query.slurm"
echo ""
echo "=========================================="


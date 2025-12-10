#!/bin/bash

# Script to create a GraphRAG package for IDUN upload

set -e

echo "=========================================="
echo "Creating GraphRAG IDUN Upload Package"
echo "=========================================="

# Get the script directory (idun-scripts)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the graphrag root directory (parent of idun-scripts)
GRAPHRAG_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to graphrag root
cd "$GRAPHRAG_ROOT"

# Output file
OUTPUT_FILE="graphrag-idun.tar.gz"

echo "Working directory: $GRAPHRAG_ROOT"
echo "Output file: $OUTPUT_FILE"
echo ""

# Create temporary directory for packaging
TMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TMP_DIR/graphrag-idun"
mkdir -p "$PACKAGE_DIR"

echo "Step 1: Copying GraphRAG source code..."
# Copy the graphrag package (source code)
mkdir -p "$PACKAGE_DIR/graphrag"
rsync -av --progress \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.pytest_cache' \
    graphrag/ "$PACKAGE_DIR/graphrag/"

# Note: .git directory not copied - using static versioning in pyproject.toml
# This avoids issues with Git metadata corruption during transfer

echo ""
echo "Step 2: Copying configuration files..."
# Copy essential config files
cp pyproject.toml "$PACKAGE_DIR/" 2>/dev/null || echo "No pyproject.toml found"
cp README.md "$PACKAGE_DIR/" 2>/dev/null || echo "No README.md found"
cp LICENSE "$PACKAGE_DIR/" 2>/dev/null || echo "No LICENSE found"
cp requirements.txt "$PACKAGE_DIR/" 2>/dev/null || echo "No requirements.txt found"
cp settings.yaml "$PACKAGE_DIR/" 2>/dev/null || echo "No settings.yaml found"

echo ""
echo "Step 3: Copying input files..."
# Copy input directory
if [ -d "input" ]; then
    mkdir -p "$PACKAGE_DIR/input"
    rsync -av --progress \
        --include='*.txt' \
        --include='*.md' \
        --exclude='*' \
        input/ "$PACKAGE_DIR/input/"
fi

echo ""
echo "Step 4: Copying ragtest directory (your working directory)..."
# Copy ragtest with input files and configuration
if [ -d "ragtest" ]; then
    mkdir -p "$PACKAGE_DIR/ragtest"
    rsync -av --progress \
        --exclude='__pycache__' \
        --exclude='output/*' \
        --exclude='cache/*' \
        --exclude='logs/*' \
        --exclude='.ipynb_checkpoints' \
        --exclude='output_old' \
        ragtest/ "$PACKAGE_DIR/ragtest/"
    
    # Create empty directories for outputs
    mkdir -p "$PACKAGE_DIR/ragtest/output"
    mkdir -p "$PACKAGE_DIR/ragtest/cache"
    mkdir -p "$PACKAGE_DIR/ragtest/logs"
fi

echo ""
echo "Step 5: Copying examples (optional)..."
# Copy examples directory (optional, comment out if not needed)
if [ -d "examples" ]; then
    mkdir -p "$PACKAGE_DIR/examples"
    rsync -av --progress \
        --exclude='__pycache__' \
        examples/ "$PACKAGE_DIR/examples/"
fi

echo ""
echo "Step 6: Copying IDUN scripts..."
# Copy IDUN scripts
mkdir -p "$PACKAGE_DIR/idun-scripts"
if [ -d "idun-scripts" ]; then
    cp idun-scripts/*.sh "$PACKAGE_DIR/idun-scripts/" 2>/dev/null && echo "  Copied shell scripts" || echo "  No .sh files found"
    cp idun-scripts/*.slurm "$PACKAGE_DIR/idun-scripts/" 2>/dev/null && echo "  Copied SLURM scripts" || echo "  No .slurm files found"
    cp idun-scripts/*.txt "$PACKAGE_DIR/idun-scripts/" 2>/dev/null || true
    cp idun-scripts/*.md "$PACKAGE_DIR/idun-scripts/" 2>/dev/null || true
    
    # Make shell scripts executable
    chmod +x "$PACKAGE_DIR/idun-scripts"/*.sh 2>/dev/null || true
    
    echo "  IDUN scripts directory contents:"
    ls -la "$PACKAGE_DIR/idun-scripts/"
else
    echo "  ERROR: idun-scripts directory not found!"
    exit 1
fi

echo ""
echo "Step 7: Creating tarball..."
# Create the tarball
cd "$TMP_DIR"
tar -czf "$GRAPHRAG_ROOT/$OUTPUT_FILE" graphrag-idun/

# Clean up
rm -rf "$TMP_DIR"

cd "$GRAPHRAG_ROOT"

# Show results
echo ""
echo "=========================================="
echo "Package created successfully!"
echo "=========================================="
echo "File: $OUTPUT_FILE"
echo "Size: $(du -h $OUTPUT_FILE | cut -f1)"
echo ""
echo "Package contents:"
tar -tzf "$OUTPUT_FILE" | head -30
echo "... (and more)"
echo ""
echo "Next steps:"
echo "1. Upload to IDUN:"
echo "   scp $OUTPUT_FILE <username>@idun-login1.hpc.ntnu.no:/cluster/work/\$USER/"
echo ""
echo "2. On IDUN, extract:"
echo "   cd /cluster/work/\$USER"
echo "   tar -xzf $(basename $OUTPUT_FILE)"
echo "   cd graphrag-idun"
echo ""
echo "3. Follow the setup guide:"
echo "   cat idun-scripts/IDUN_SETUP_GUIDE.md"
echo "=========================================="


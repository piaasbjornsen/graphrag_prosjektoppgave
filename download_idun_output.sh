#!/bin/bash
# ==============================================
# Download GraphRAG output files from IDUN
# Usage: ./download__idun.sh <job_id>
# Example: ./download_idun_output.sh 23129729
# ==============================================

# Input argument: Job ID
JOB_ID=$1

# Check input
if [ -z "$JOB_ID" ]; then
  echo "❌ Usage: $0 <job_id>"
  exit 1
fi

# --- Configuration ---
REMOTE_USER="<ntnu-username>"  # your NTNU username
REMOTE_HOST="idun.hpc.ntnu.no"  # IDUN hostname
REMOTE_BASE="/cluster/work/<ntnu-username>/graphrag-idun" # where on IDUN the data is located
LOCAL_BASE="/your/local/path/graphrag-idun-output/${JOB_ID}"  # local path to save the data

# --- Create local directories ---
echo "📂 Creating local directories..."
mkdir -p "${LOCAL_BASE}/ragtest/logs"
mkdir -p "${LOCAL_BASE}/ragtest/cache/extract_graph"
mkdir -p "${LOCAL_BASE}/ragtest/output"
mkdir -p "${LOCAL_BASE}/logs"

# --- Download individual log file ---
echo "⬇️  Downloading indexing-engine.log..."
if ! scp "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/ragtest/logs/indexing-engine.log" \
    "${LOCAL_BASE}/ragtest/logs/indexing-engine.log" 2>/dev/null; then
  echo "⚠️  Warning: indexing-engine.log not found or failed to download"
fi

# --- Download extract_graph folder recursively ---
echo "⬇️  Downloading extract_graph folder..."
if ! scp -r "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/ragtest/cache/extract_graph/"* \
    "${LOCAL_BASE}/ragtest/cache/extract_graph/" 2>/dev/null; then
  echo "⚠️  Warning: extract_graph folder not found or failed to download"
fi

# --- Download output folder recursively ---
echo "⬇️  Downloading output folder..."
if ! scp -r "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/ragtest/output/"* \
    "${LOCAL_BASE}/ragtest/output/" 2>/dev/null; then
  echo "⚠️  Warning: output folder not found or failed to download"
fi

# --- Download logs folder recursively ---
echo "⬇️  Downloading logs folder..."
if ! scp -r "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/logs/"* \
    "${LOCAL_BASE}/logs/" 2>/dev/null; then
  echo "⚠️  Warning: logs folder not found or failed to download"
fi

echo "✅ Download process completed. Files saved to:"
echo "   ${LOCAL_BASE}"

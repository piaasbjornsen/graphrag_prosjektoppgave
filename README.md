# GraphRAG Prosjektoppgave PoC

# Pre-Processing

## 1. Download directories

- Create a workspace

```bash
mkdir my_project
```

- Download graphrag-local-ollama

https://github.com/TheAiSingularity/graphrag-local-ollama

## 2. Set up Environment

- Create a conda env

```bash
conda create -n my_project python=3.10
conda activate my_project
```

- Download ollama and models
- Navigate into the repository

```bash
cd my_project/graphrag-local-ollama/
```

- Install the requirements

```bash
pip install -e .
```

- Create a input directory

```bash
mkdir -p ./ragtest/input
```

- Upload the data

```bash
cp input/* ./ragtest/input
```

- Initialize the ./ragtest folder to create the required files

```bash
python -m graphrag.index --init --root ./ragtest
```

- Move the settings.yaml

```bash
cp settings.yaml ./ragtest
```

- Change the settings files if wanted

# Graph Extraction

## 1. Run graph indexing

- Locally:

```bash
python -m graphrag.index --root ./ragtest
```

### Run graph indexing on IDUN

- Package the application

* Move the idun-scrips folder into the graphrag-local-ollama folder

```bash
cp idun-scripts graphrag-local-ollama
```

- run the idun-scripts/create_idun_package.sh script.

```bash
 my_project/graphrag-local-ollama
./idun-scripts/create_idun_package.sh
```

This creates a .tar.gz file you can upload to IDUN

### Upload the package to IDUN

- Connect to IDUN - make sure you are on VPN

```bash
ssh <username>@idun-login1.hpc.ntnu.no
```

- From you local repo upload to IDUN

```bash
cd my_project/
scp ./graphrag-local-ollama/graphrag-idun.tar.gz piaas@idun-login1.hpc.ntnu.no:/cluster/work/<username>/
```

- From you IDUN terminal

```bash
cd /cluster/work/$USER/
tar -xzf graphrag-idun.tar.gz
cd graphrag-idun
bash idun-scripts/setup_env.sh
```

### Submit job

```bash
sbatch idun-scripts/idun_indexing.slurm
```

### Useful commands:

- squeue -u \<userame\>: Watch you queued jobs
- watch the output:
  - tail -f logs/graphrag*index*<job_id>.out
  - tail -f logs/graphrag*index*<job_id>.err
  - tail -f logs/graphrag*query*<job_id>.out
  - tail -f logs/graphrag*query*<job_id>.err
- Remove from IDUNrm:
  - rm -rf graphrag-idun.tar.gz

## 2. Download graph

### Run download script

- From you local workspace

```bash
sbatch ./download__idun.sh <job_id>
```

# RDF Conversion

The RDF conversion pipeline converts GraphRAG parquet output to DBpedia-compatible RDF format.

## Prerequisites

- Python 3.10+ (3.12 recommended)
- GraphRAG parquet output files:
  - `create_final_entities.parquet`
  - `create_final_relationships.parquet`

## Local Setup

### 1. Install Dependencies

```bash
cd RDF-conversion
pip install -r requirements.txt
```

### 2. Configure Input Path

**Option 1: Edit the default path (easiest for repeated runs)**

Edit `run_pipeline.py` and change the `DEFAULT_ARTIFACTS` variable at the top (around line 32):

```python
DEFAULT_ARTIFACTS = "../path/to/artifacts"
```

**Option 2: Use command-line argument (no file editing needed)**

```bash
python run_pipeline.py --artifacts /path/to/artifacts
```

**Note:** The path should point to the directory containing:

- `create_final_entities.parquet`
- `create_final_relationships.parquet`

### 3. Set Up Ollama (for LLM refinement)

The pipeline uses Ollama for step 2 (LLM refinement). Make sure Ollama is running:

```bash
# Start Ollama server
ollama serve

# Pull required model (in another terminal)
ollama pull mistral
```

### 4. Run the Pipeline

Run all steps (uses DEFAULT_ARTIFACTS from run_pipeline.py):

```bash
python run_pipeline.py
```

### Output

The final RDF file will be saved to:

```
RDF-conversion/output/graphrag_dbo.ttl
```

Intermediate outputs are also saved:

- `step1_extracted.json` - Raw extracted data
- `step2_refined.json` - LLM-refined terms
- `step3_mapped.json` - DBpedia-mapped terms


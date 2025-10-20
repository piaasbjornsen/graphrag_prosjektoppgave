# graphrag_prosjektoppgave

# 1. Create a workspace 
```bash 
mkdir my_project
 ```

 # 2. Download graphrag-local-ollama
 https://github.com/TheAiSingularity/graphrag-local-ollama

* Create a conda env 
```bash 
conda create -n my_project python=3.10
conda activate my_project
 ```
 * Download ollama and models
 * Navigate into the repository 
```bash 
cd my_project/graphrag-local-ollama/
 ```
 * Install the requirements 
```bash 
pip install -e .
 ```
 * Create a input directory 

```bash 
mkdir -p ./ragtest/input 
 ```
 * Upload the data you want to index - yoy may use the graphrag-local-ollama default input 
```bash 
cp input/* ./ragtest/input
  ```
 * Initialize the ./ragtest folder to create the required files
```bash 
python -m graphrag.index --init --root ./ragtest
  ```
  * Move the settings.yaml
```bash 
cp settings.yaml ./ragtest
  ```
* Change the settings files if wanted


 # 3A. Run graph indexing locally 
 ```bash 
python -m graphrag.index --root ./ragtest
  ```


# 3B Run graph indexing on IDUN
1. Package the application
* move the idun-scrips folder into the graphrag-local-ollama folder
```bash 
cp idun-scripts graphrag-local-ollama
  ```

 ```bash 
cd my_project/graphrag-local-ollama
./idun-scripts/create_idun_package.sh
  ```
  This creates a .tar.gz file you can upload to IDUN
1. Upload the package to IDUN
* Connect to IDUN - make sure you are on VPN
 ```bash 
ssh <username>@idun-login1.hpc.ntnu.no
  ```

* From you local repo upload to IDUN
 ```bash 
 cd my_project/graphrag-local-ollama
 scp graphrag-idun.tar.gz piaas@idun-login1.hpc.ntnu.no:/cluster/work/<username>/
  ```
* From you IDUN terminal
 ```bash 
cd /cluster/work/$USER/
tar -xzf graphrag-idun.tar.gz
cd graphrag-idun
bash idun-scripts/setup_env.sh
  ```

1. Run indexing
```bash
sbatch idun-scripts/idun_indexing.slurm
```   
*
squeue -u piaas
* watch the output
tail -f logs/graphrag_index_*.out
tail -f logs/graphrag_index_*.err






 scp graphrag-local-ollama/input/book.txt piaas@idun-login1.hpc.ntnu.no:/cluster/work/piaas/graphrag-idun/ragtest/input


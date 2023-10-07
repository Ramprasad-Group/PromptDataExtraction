#!/usr/bin/env bash

# Run cron jobs.
# List current cron jobs with crontab -l
# Edit user's cron jobs with crontab -e

# Example line to run every 6 hours:
# 0 */6 * * * /data/akhlak/PromptDataExtraction/cron.sh &> /data/akhlak/PromptDataExtraction/cron.log

# Detect Current Working Directory.
# ==============================================================================
MY_PATH="$(dirname -- "${BASH_SOURCE[0]}")"            # relative
MY_PATH="$(cd -- "$MY_PATH" && pwd)"    # absolutized and normalized
if [[ -z "$MY_PATH" ]] ; then
  exit 1  # fail
fi

cd $MY_PATH
echo "CWD: $MY_PATH"

# Activate conda environment.
# ==============================================================================
eval "$(/data/akhlak/miniconda3/condabin/conda shell.bash hook)"
conda activate "${MY_PATH}/_conda_env"
export LD_LIBRARY_PATH=$(realpath _conda_env/lib64):$LD_LIBRARY_PATH
export PYTHONPATH=.
python --version

# Execute the cron job.
# ==============================================================================
python  backend --dir runs/ner-pipeline/ \
        ner-filtered -m g-ner-pipeline -l 10000 


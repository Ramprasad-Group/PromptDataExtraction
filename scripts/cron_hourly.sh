#!/usr/bin/env bash

# UPDATE!!
eval "$(/data/akhlak/miniconda3/condabin/conda shell.bash hook)"

# crontab -l        <-- list
# crontab -e        <-- edit

# Example line to run every hour:
# 0 */1 * * * /data/akhlak/PromptDataExtraction/scripts/hourly.sh &> hourly.log

# Detect Current Working Directory.
# ==============================================================================
MY_PATH="$(dirname -- "${BASH_SOURCE[0]}")"            # relative
MY_PATH="$(cd -- "$MY_PATH" && pwd)"    # absolutized and normalized
if [[ -z "$MY_PATH" ]] ; then
  exit 1  # fail
fi

cd $MY_PATH/..
echo "CWD: $MY_PATH"

# Activate conda environment.
# ==============================================================================
conda activate "${MY_PATH}/_conda_env"
export LD_LIBRARY_PATH=$(realpath _conda_env/lib64):$LD_LIBRARY_PATH
export PYTHONPATH=.
python --version

# Execute the cron job.
# ==============================================================================

# GENERAL NER PIPELINE
python  backend --dir runs/ner-pipeline/ \
        ner-filtered -m g-ner-pipeline -l 10000 &> $MY_PATH/ner-pipeline.out &

# GENERAL NER FILTER
python  backend --dir runs/filters/ner/ \
        filter-by-ner -l 10000 &> $MY_PATH/ner-filter.out &

# Fix the values with +/- in them.
# python backend/ fix-data --save 
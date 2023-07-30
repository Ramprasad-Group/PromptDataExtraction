# Polymer Information Extraction

This repo contains data extraction code using the OpenAI API. The performance of GPT3.5 is benchmarked on the task of extracting bandgap and Tg through few-shot in-context learning.

## Requirements and Setup

- Python 3.9.16
- Pytorch (version 1.13.1)
- Transformers (version 4.17.0)

You can install all required Python packages using the provided environment.yml file and by running the shell script setup.sh as ```bash setup.sh```. Ensure that conda is installed on the system.

## Running the code

The script for obtaining benchmark metrics of bandgap and Tg data extraction can be obtained by using the below command. Change the parameters at the head of the bash script to the experiments you wish to run. Ensure that you have entered your API Key in PromptDataExtraction/configs/config.py. API Key can be obtained by creating an account with OpenAI and setting up the key through the admin dashboard.

```bash
bash ./scripts/run.sh

```

Bandgap and Tg data can be extracted from the body of papers by running the following command:

```bash
python full_text_extraction.py --use_llm --use_conventional_pipeline
    
```

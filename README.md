# Prompt Data Extraction
Python module and scripts to run automated data extraction pipelines built using MaterialsBERT, GPT-3.5 and LlaMa 2 models.

Developed for the data extraction methods described in:
> **Data Extraction from Polymer Literature using Large Language Models.** \
> S. Gupta, A. Mahmood, P. Shetty, A. Adeboye and R. Ramprasad, \
> 2024 (Submitted)
<!-- > **Nature Machine Intelligence**, 2024 -->
<!-- > DOI: [https://doi.org/](https://doi.org/ "DOI") -->

The extracted data can be visualized freely at [https://polymerscholar.org](https://polymerscholar.org).

## Installation
1. Make sure you have [conda](https://docs.anaconda.com/free/miniconda/index.html) installed.
2. Clone the git repository: `git clone https://github.com/Ramprasad-Group/PromptDataExtraction && cd PromptDataExtraction`.
3. Source the `env.sh` script from a bash terminal. It will setup a new conda environment and install the required python packages, compilers and CUDA libraries.
4. A `settings.yaml` file will be generated with default configuration options.
5. If the environment was already installed before, source the `env.sh` script to activate it.

This package requires a PostgreSQL server to store and manage literature extracted data.

The *MaterialsBERT* model can be downloaded from the
[Huggingface Hub](https://huggingface.co/pranav-s/MaterialsBERT)
and the path to the model should be set in the settings.

## Usage
Edit the newly created `settings.yaml` file to update required paths, usernames, passwords, database connection details, API keys, *etc.*

The following scripts are available to process multiple properties, models and articles:

- `parse_papers.py`: Parse and extract paragraphs from a corpus directory containing full text HTML or XML articles.

- `filter_polymer_papers.py`: Identify the polymer papers using the Title and/or the Abstract of the articles.

- `run_heuristic_filters.sh`: Filter the polymer-related paragraphs using property specific heuristic filters.

- `run_ner_filters.sh`: Filter the heuristically filtered paragraphs using NER filters and MaterialsBERT.

- `run_methods.sh`: Add new extraction method/configuration to the database.

- `run_ner_pipeline.sh`: Perform data extraction on the NER-filtered paragraphs
using NER-based MaterialsBERT pipeline.

- `run_gpt_pipeline.sh`: Perform data extraction on the NER-filtered paragraphs
using LLM pipeline.

- `run_post_process_ner.sh`: Run post-processing validatation and filtering on the
NER pipeline extracted data.

- `run_post_process_llm.sh`: Run post-processing validatation and filtering on the
LLM pipeline extracted data.


These scripts interface with the `backend` module. More fine-grained tasks can be performed by the module. To list the available commands, run `python backend -h`.


## About
Developed by: \
Ramprasad Research Group, \
MSE, Georgia Institute of Technology.

Copyright 2024 Georgia Tech Research Corporation. \
All Rights Reserved. See the [LICENSE](LICENSE) file for details.

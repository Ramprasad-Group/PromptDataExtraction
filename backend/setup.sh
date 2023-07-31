#!/bin/bash

conda env create -f environment.yml
conda activate prompt_data_extraction
python -m spacy download en_core_web_sm
pip install -e .
cd ../record_extraction_pipeline
pip install -e .
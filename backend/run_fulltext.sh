#!/usr/bin/env bash

python prompt_extraction/full_text_extraction.py \
    --prompt_index 5 \
    --out_dir Run_Test \
    --mode  Tg \
    --collection_output_name fulltext_test \
    --experiment_name test_run \
    --debug


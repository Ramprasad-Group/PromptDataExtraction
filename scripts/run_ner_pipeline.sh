#!/bin/bash

method_names=(
    # "cs-ner-bert-sel1k"
    "eab-ner-bert-sel1k"
    "fs-ner-bert-sel1k"
    "hardness-ner-bert-sel1k"
    "is-ner-bert-sel1k"
    "tc-ner-bert-sel1k"
    "td-ner-bert-sel1k"
    "ts-ner-bert-sel1k"
    "ym-ner-bert-sel1k"
    "ionic_cond-ner-bert-sel1k"
    "loi-ner-bert-sel1k"
    "lcst-ner-bert-sel1k"
    "o2_perm-ner-bert-sel1k"
    "ri-ner-bert-sel1k"
    "ucst-ner-bert-sel1k"
    "wca-ner-bert-sel1k"
    "wu-ner-bert-sel1k"
    "sd-ner-bert-sel1k"
    "density-ner-bert-sel1k"
    "iec-ner-bert-sel1k"
    # "methanol_perm-ner-bert-sel1k"
    )


nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/sel1k"
chmod +w "$nohup_folder"

for method_name in "${method_names[@]}"; do
    log_file="np_${method_name}.log"
    output_file="${nohup_folder}/np_${method_name}.out"

    echo "Running ner pipeline for: $method_name"
    nohup python backend --logfile "$log_file" ner-filtered -m "$method_name" >"$output_file" 2>&1 &
done

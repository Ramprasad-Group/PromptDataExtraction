#!/bin/bash

method_names=(
    # "tg-ner-bert-sel1k-no-unit"
    # "tm-ner-bert-sel1k-no-unit"
    # "td-ner-bert-sel1k-no-unit"
    # "tc-ner-bert-sel1k-no-unit"
    # "ts-ner-bert-sel1k-no-unit"
    # "ym-ner-bert-sel1k-no-unit"
    # "cs-ner-bert-sel1k-no-unit"
    # "eab-ner-bert-sel1k-no-unit"
    # "fs-ner-bert-sel1k-no-unit"
    # "is-ner-bert-sel1k-no-unit"
    # "iec-ner-bert-sel1k-no-unit"
    # "ionic_cond-ner-bert-sel1k-no-unit"
    # "wca-ner-bert-sel1k-no-unit"
    # "dc-ner-bert-sel1k-no-unit"
    # "density-ner-bert-sel1k-no-unit"
    # "ucst-ner-bert-sel1k-no-unit"
    # "loi-ner-bert-sel1k-no-unit"
    # "bandgap-ner-bert-sel1k-no-unit"
    # "hardness-ner-bert-sel1k-no-unit"
    # "lcst-ner-bert-sel1k-no-unit"
    # "co2_perm-ner-bert-sel1k-no-unit"
    # "o2_perm-ner-bert-sel1k-no-unit"
    "h2_perm-ner-bert-sel1k-no-unit"
    "ct-ner-bert-sel1k-no-unit"
    "ri-ner-bert-sel1k-no-unit"
    "wu-ner-bert-sel1k-no-unit"
    "sd-ner-bert-sel1k-no-unit"
    "methanol_perm-ner-bert-sel1k-no-unit"
    )


nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/sel1k/np2"
chmod +w "$nohup_folder"

for method_name in "${method_names[@]}"; do
    log_file="np_${method_name}.log"
    output_file="${nohup_folder}/np_${method_name}.out"

    echo "Running ner pipeline for: $method_name"
    nohup python backend --logfile "$log_file" ner-filtered -m "$method_name" >"$output_file" 2>&1 &
done

#!/bin/bash

method_names=(
  # "bandgap-gpt35-sel1k"
  # "co2_perm-gpt35-sel1k"
  # "cs-gpt35-sel1k"
  "ct-gpt35-sel1k"
  "dc-gpt35-sel1k"
  # "density-gpt35-sel1k"
  # "eab-gpt35-sel1k"
  # "fs-gpt35-sel1k"
  # "hardness-gpt35-sel1k"
  # "h2_perm-gpt35-sel1k"
  # "iec-gpt35-sel1k"
  # "ionic_cond-gpt35-sel1k"
  # "is-gpt35-sel1k"
  # "lcst-gpt35-sel1k"
  # "loi-gpt35-sel1k"
  # "methanol_perm-gpt35-sel1k"
  # "o2_perm-gpt35-sel1k"
  # "ri-gpt35-sel1k"
  # "sd-gpt35-sel1k"
  # "tc-gpt35-sel1k"
  # "td-gpt35-sel1k"
  # "tm-gpt35-sel1k"
  # "ts-gpt35-sel1k"
  # "tg-gpt35-sel1k"
  # "ucst-gpt35-sel1k"
  # "wca-gpt35-sel1k"
  # "wu-gpt35-sel1k"
  # "ym-gpt35-sel1k"
)

nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/sel1k/gpt"
chmod +w "$nohup_folder"

for method_name in "${method_names[@]}"; do
    log_file="gpt/${method_name}.log"
    output_file="${nohup_folder}/${method_name}.out"

    echo "Running llm (gpt) pipeline for: $method_name"
    nohup python backend --logfile "$log_file" llm-pipeline -m "$method_name" >"$output_file" 2>&1 &
done
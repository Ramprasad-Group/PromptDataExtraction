#!/bin/bash

method_names=(
  "bandgap-gpt35-similar-full"
  # "co2_perm-gpt35-similar-full"
  # "cs-gpt35-similar-full"
  # "ct-gpt35-similar-full"
  # "dc-gpt35-similar-full"
  # "density-gpt35-similar-full"
  # "eab-gpt35-similar-full"
  # "fs-gpt35-similar-full"
  # "hardness-gpt35-similar-full"
  # "h2_perm-gpt35-similar-full"
  # "iec-gpt35-similar-full"
  # "ionic_cond-gpt35-similar-full"
  # "is-gpt35-similar-full"
  # "lcst-gpt35-similar-full"
  # "loi-gpt35-similar-full"
  # "methanol_perm-gpt35-similar-full"
  # "o2_perm-gpt35-similar-full"
  # "ri-gpt35-similar-full"
  # "sd-gpt35-similar-full"
  # "tc-gpt35-similar-full"
  # "td-gpt35-similar-full"
  # "tm-gpt35-similar-full"
  # "ts-gpt35-similar-full"
  # "tg-gpt35-similar-full"
  # "ucst-gpt35-similar-full"
  # "wca-gpt35-similar-full"
  # "wu-gpt35-similar-full"
  # "ym-gpt35-similar-full"
)

nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/full-corpus/gpt"
chmod +w "$nohup_folder"

for method_name in "${method_names[@]}"; do
    log_file="gpt/${method_name}.log"
    output_file="${nohup_folder}/${method_name}.out"

    echo "Running llm (gpt) pipeline for: $method_name"
    nohup python backend --logfile "$log_file" llm-pipeline -m "$method_name" -l >"$output_file" 2>&1 &
done
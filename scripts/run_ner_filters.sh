#!/bin/bash

filter_names=(
	# "bandgap_ner_full"
  # "tg_ner_full"
  # "co2_perm_ner_full"
  # "cs_ner_full"
  # "ct_ner_full"
  # "dc_ner_full"
  # "density_ner_full"
  # "eab_ner_full"
  # "fs_ner_full"
  # "hardness_ner_full"
  # "h2_perm_ner_full"
  "iec_ner_full"
  # "ionic_cond_ner_full"
  # "is_ner_full"s
  # "lcst_ner_full"
  # "loi_ner_full"
  # "methanol_perm_ner_full"
  # "o2_perm_ner_full"
  # "ri_ner_full"
  # "sd_ner_full"
  # "tc_ner_full"
  # "td_ner_full"
  # "tm_ner_full"
  # "ts_ner_full"
  # "ucst_ner_full"
  "wca_ner_full"
  # "wu_ner_full"
  # "ym_ner_full"
	)


python_script="backend/"
nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/full-corpus/ner"

chmod +w "$nohup_folder"

for filter_name in "${filter_names[@]}"; do
    log_file="ner/${filter_name}.log"
    output_file="${nohup_folder}/ner_${filter_name}.out"

    echo "Running ner filter: $filter_name"
    nohup python "$python_script" --logfile "$log_file" ps-ner-filter --filter "$filter_name"  >"$output_file" 2>&1 &

done
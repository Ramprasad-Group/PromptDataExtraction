#!/bin/bash

filter_names=(
    "property_ionic_cond"
    "property_wca" 
    "property_dc" 
    "property_density" 
	"property_loi" 
	"property_iec"
	"property_lcst"
	"property_ucst" 
	"property_co2_perm" 
	"property_ct" 
	"property_ri" 
	"property_wu"
	"property_sd"
	"property_o2_perm" 
	"property_h2_perm"
	"property_methanol_perm" )

python_script="backend/"
nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/sel1k"

chmod +w "$nohup_folder"

for filter_name in "${filter_names[@]}"; do
    log_file="hf_${filter_name}.log"
    output_file="${nohup_folder}/hf_${filter_name}.out"

    echo "Running filter: $filter_name"
    nohup python "$python_script" --logfile "$log_file" heuristic-filter --filter "$filter_name"  >"$output_file" 2>&1 &
    # echo "Filter $filter_name completed"
done

#!/bin/bash

filter_names=(
		# "property_tg"
		# "property_bandgap"
		# "property_tm"
		# "property_td"
		# "property_thermal_conductivity"
		# "property_ts"
		# "property_ym"
		# "property_cs"
		# "property_eab"
		# "property_hardness"
    # "property_ionic_cond"
    # "property_wca" 
    # "property_dc" 
    # "property_density" 
		# "property_loi" 
		# "property_iec"
		# "property_lcst"
		# "property_ucst" 
		# "property_co2_perm" 
		# "property_ct" 
		# "property_ri" 
		# "property_wu"
		"property_sd"
		# "property_o2_perm" 
		# "property_h2_perm"
		# "property_methanol_perm" 
	)

python_script="backend/"
nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/full-corpus/hf"

chmod +w "$nohup_folder"

for filter_name in "${filter_names[@]}"; do
    log_file="hf/${filter_name}.log"
    output_file="${nohup_folder}/${filter_name}.out"

    echo "Running heuristic filter: $filter_name"
    nohup python "$python_script" --logfile "$log_file" heuristic-filter --filter "$filter_name" -l 15000000 >"$output_file" 2>&1 &

done

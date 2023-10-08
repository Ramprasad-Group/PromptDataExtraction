#!/bin/bash


hf_filter_names=(
	"tg-hf-sel1k"
	"bandgap-hf-sel1k"
	"tm-hf-sel1l"
	"td-hf-sel1k"
	"tc-ner-sel1k"
	"ts-ner-sel1k"
	"ym-ner-sel1k"
	"cs-ner-sel1k"
	"eab-ner-sel1k"
	"fs-ner-sel1k"
	"is-ner-sel1k"
	"iec-ner-sel1k"
  "ionic_cond-hf-sel1k"
  "wca-hf-sel1k" 
  "dc-hf-sel1k" 
  "density-hf-sel1k" 
	"loi-hf-sel1k" 
	"iec-hf-sel1k"
	"lcst-hf-sel1k"
	"ucst-hf-sel1k" 
	"co2_perm-hf-sel1k" 
	"ct-hf-sel1k" 
	"ri-hf-sel1k" 
	"wu-hf-sel1k"
	"sd-hf-sel1k"
	"o2_perm-hf-sel1k" 
	"h2_perm-hf-sel1k"
	"methanol_perm-hf-sel1k" )


python_script="backend/"
nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/sel1k"

chmod +w "$nohup_folder"

for filter_name in "${filter_names[@]}"; do
    log_file="hf_${filter_name}.log"
    output_file="${nohup_folder}/hf_${filter_name}.out"

    echo "Running filter: $filter_name"
    nohup python "$python_script" --logfile "$log_file" ps-ner-filter --filter "$filter_name"  >"$output_file" 2>&1 &
    # echo "Filter $filter_name completed"
done
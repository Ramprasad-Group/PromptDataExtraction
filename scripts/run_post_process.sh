#!/bin/bash

method_names=(
#     "tg-gpt35-similar-full"
    "sd-gpt35-similar-full"
    # "bandgap-gpt35-similar-full"
#     "hardness-gpt35-similar-full"
#     "td-gpt35-similar-full"
#     "co2_perm-gpt35-similar-full"
#     "cs-gpt35-similar-full"
#     "ct-gpt35-similar-full"
#     "dc-gpt35-similar-full"
#     "density-gpt35-similar-full"
#     "eab-gpt35-similar-full"
#     "fs-gpt35-similar-full"
#     "h2_perm-gpt35-similar-full"
#     "iec-gpt35-similar-full"
#     "ionic_cond-gpt35-similar-full"
#     "is-gpt35-similar-full"
#     "lcst-gpt35-similar-full"
#     "loi-gpt35-similar-full"
#     "methanol_perm-gpt35-similar-full"
#     "o2_perm-gpt35-similar-full"
#     "ri-gpt35-similar-full"
#     "tc-gpt35-similar-full"
#     "tm-gpt35-similar-full"
#     "ts-gpt35-similar-full"
#     "ucst-gpt35-similar-full"
#     "wca-gpt35-similar-full"
#     "wu-gpt35-similar-full"
#     "ym-gpt35-similar-full"
)

nohup_folder="."
chmod +w "$nohup_folder"


for method_name in "${method_names[@]}"; do
    log_dir="gpt-full/post-process/${method_name}"
    outfile="${nohup_folder}/post-proc.${method_name}.out"

    echo "Running post-processing for: $method_name" | tee $outfile

    # 1. Fix the values with +/- in them.
    python backend --logfile $log_dir/fix_data.log fix-data \
            -m "$method_name" | tee -a $outfile

    # 2a. Filter the values that have known property name.
    python backend --logfile $log_dir/filter_name.log filter-data \
                -f name --remove \
                -m "$method_name" | tee -a $outfile

    # 2b. Filter the values that have known property unit.
    python backend --logfile $log_dir/filter_unit.log filter-data \
                -f unit --remove \
                -m "$method_name" | tee -a $outfile

    # 2c. Filter the values that have known property range.
    python backend --logfile $log_dir/filter_range.log filter-data \
                -f range --remove \
                -m "$method_name" | tee -a $outfile

    # 2d. Filter the values that have known polymer material name.
    python backend --logfile $log_dir/filter_polymers.log filter-data \
                -f polymer \
                -m "$method_name" | tee -a $outfile

    # 2e. Filter the values that have para text look like table.
    python backend --logfile $log_dir/filter_tables.log filter-data \
                -f table \
                -m "$method_name" | tee -a $outfile

    # 3. Calculate confidence and error scores using the filtered items.
    # Add to the extract_data table.
    python backend --logfile $log_dir/extract_data.log extract-data \
            -m "$method_name" | tee -a $outfile

done

# 4. Export the final valid data for polymerscholar.
python backend --logfile $log_dir/export_data.log export-data | tee -a $outfile

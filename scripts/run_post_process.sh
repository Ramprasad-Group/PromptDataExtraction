#!/bin/bash

method_names=(
#     "tg-gpt35-similar-full"
    "sd-gpt35-similar-full"
#     "bandgap-gpt35-similar-full"
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
    log_dir="runs/gpt-full/post-process/${method_name}"
    outfile="${nohup_folder}/${method_name}.out"

    echo "Running post-processing for: $method_name" | tee $outfile

    # 1. Fix the values with +/- in them.
    python backend --dir $log_dir fix-data \
            -m "$method_name" | tee -a $outfile

    # 2. Filter the values that are within range,
    #   has appropriate property name etc.
    python backend --dir $log_dir filter-data --redo \
            -m "$method_name" | tee -a $outfile

    # 3. Calculate confidence and error scores using the filtered data.
    python backend --dir $log_dir extract-data \
            -m "$method_name" | tee -a $outfile

done

# 4. Export the final valid data table.
python backend --dir $log_dir export-data -o | tee -a $outfile

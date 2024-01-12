#!/bin/bash

method_names=(
    "tg-gpt35-similar-full"
    "bandgap-gpt35-similar-full"
    # "sd-gpt35-similar-full"
    # "hardness-gpt35-similar-full"
    # "td-gpt35-similar-full"
    # "co2_perm-gpt35-similar-full"
    # "cs-gpt35-similar-full"
    # "ct-gpt35-similar-full"
#     "dc-gpt35-similar-full"
#     "density-gpt35-similar-full"
    # "eab-gpt35-similar-full"
    # "fs-gpt35-similar-full"
    # "h2_perm-gpt35-similar-full"
    # "iec-gpt35-similar-full"
#     "ionic_cond-gpt35-similar-full"
    # "is-gpt35-similar-full"
    # "lcst-gpt35-similar-full"
    # "loi-gpt35-similar-full"
#     "methanol_perm-gpt35-similar-full"
#     "o2_perm-gpt35-similar-full"
    # "n2_perm-gpt35-similar-full"
    # "ch4_perm-gpt35-similar-full"
    # "ri-gpt35-similar-full"
    # "tc-gpt35-similar-full"
    # "tm-gpt35-similar-full"
#     "ts-gpt35-similar-full"
    # "ucst-gpt35-similar-full"
    # "wca-gpt35-similar-full"
    # "wu-gpt35-similar-full"
    # "ym-gpt35-similar-full"
)

for method_name in "${method_names[@]}"; do
    log_dir="gpt-full/post-process/${method_name}"
    echo "Running post-processing for: $method_name"

#     # 1. Fix the values with +/- in them.
#     python backend --logfile $log_dir/fix_data.log \
#             fix-error -m "$method_name"

    # 1b. Update material names and class.
    python backend --logfile $log_dir/fix_material.log \
            fix-material -m "$method_name" --save

#     # 2a. Filter the values that have known property name.
#     python backend --logfile $log_dir/filter_name.log \
#             filter-llm-data -m "$method_name" -f name --remove

#     # @todo: Normalize units here (if needed).
#     # exit 0

#     # 2b. Filter the values that have known property unit.
#     python backend --logfile $log_dir/filter_unit.log \
#             filter-llm-data -m "$method_name" -f unit --remove

#     # 2c. Filter the values that have known property range.
#     python backend --logfile $log_dir/filter_range.log \
#             filter-llm-data -m "$method_name" -f range --remove

#     # 2d. Filter the values that have known polymer material name.
#     python backend --logfile $log_dir/filter_polymers.log \
#             filter-llm-data -m "$method_name" -f polymer

#     # 2e. Filter the values that have para text looking like a table.
#     python backend --logfile $log_dir/filter_tables.log \
#             filter-llm-data -m "$method_name" -f table

#     # 3. Calculate confidence and error scores using the filtered items.
#     # Add to the extract_data table.
#     python backend --logfile $log_dir/extract_data.log \
#             extract-llm-data -m "$method_name"

done

# 4. Export the final valid data for polymerscholar.
python backend --logfile $log_dir/export_data.log export-data

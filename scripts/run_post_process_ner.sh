#!/bin/bash

prop_names=(
# tg
# bandgap
sd
# hardness
# td
# co2_perm
# cs
# ct
# dc
# density
# eab
# fs
# h2_perm
# iec
# ionic_cond
# is
# lcst
# loi
# methanol_perm
# o2_perm
# ri
# tc
# tm
# ts
# ucst
# wca
# wu
# ym
)

# 1. Fix all values with +/- in them.
# python backend --logfile $log_dir/fix_data.log fix-data -m g-ner-pipeline

for prop_name in "${prop_names[@]}"; do
    log_dir="ner-pipeline/post-process/${prop_name}"
    echo "Running post-processing for: $prop_name"

    # 2a. Filter the values that have known property name.
    python backend --logfile $log_dir/filter_name.log \
            filter-ner-data -p "$prop_name" -f name

    # # @todo: Normalize units here (if needed).

    # # 2b. Filter the values that have known property unit.
    python backend --logfile $log_dir/filter_unit.log \
            filter-ner-data -p "$prop_name" -f unit 

    # # 2c. Filter the values that have known property range.
    python backend --logfile $log_dir/filter_range.log \
            filter-ner-data -p "$prop_name" -f range

    # # 2d. Filter the values that have known polymer material name.
    python backend --logfile $log_dir/filter_polymers.log \
            filter-ner-data -p "$prop_name" -f polymer

    # # 2e. Filter the values that have para text looking like a table.
    python backend --logfile $log_dir/filter_tables.log \
            filter-ner-data -p "$prop_name" -f table

    # # 3. Calculate confidence and error scores using the filtered items.
    # #    Add to the extract_data table.
    python backend --logfile $log_dir/extract_data.log \
            extract-ner-data -p "$prop_name"

done

# 4. Export the final valid data for polymerscholar.
# python backend --logfile $log_dir/export_data.log export-data

#!/bin/bash
# DATASET can take value Tg or bandgap
# SAMPLING can take the value random or error_diversity or baseline_diversity

OUT_DIR="Run_Output"
DATASET="bandgap"
SAMPLING="baseline_diversity"
EXPERIMENTBASE="abstracts_$SAMPLING"
ERROR_FILE="$OUT_DIR/output/${DATASET}/llm_error_doi_list.json"
echo $EXPERIMENTBASE
echo $ERROR_FILE

start=5
end=0

mkdir -p $OUT_DIR/log $OUT_DIR/output $OUT_DIR/data

# Iterate over the range of numbers
for ((count=start; count>=end; count--)); do
    echo
    echo "Few shot count: ${count}"
    LOGFILE="$OUT_DIR/log/${DATASET}_${EXPERIMENTBASE}_${count}shot.log"
    EXPERIMENTNAME="${EXPERIMENTBASE}_${count}shot"

    echo "Log file location: ${LOGFILE}"
    echo "Name of experiment: ${EXPERIMENTNAME}"

    python prompt_extraction/run_inference.py \
                --experiment_name $EXPERIMENTNAME \
                --doi_error_list_file $ERROR_FILE \
                --mode $DATASET \
                --out_dir $OUT_DIR \
                --prompt_index 5 \
                --seed_sampling $SAMPLING \
                --seed_count $count &> $LOGFILE
done

echo "Done"

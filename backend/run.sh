#!/bin/bash
# DATASET can take value Tg or bandgap
# SAMPLING can take the value random or error_diversity

OUT_DIR="RunOut"
DATASET="Tg"
SAMPLING="random"
EXPERIMENTBASE="test_5_$SAMPLING"
ERROR_FILE="$OUT_DIR/output/${DATASET}/prompt_5_0_shot/llm_error_doi_list.json"
echo $EXPERIMENTBASE
echo $ERROR_FILE
start=1
end=1

# Iterate over the range of numbers
for ((count=start; count<=end; count++)); do

    echo "Few shot count: ${count}"
    LOGFILE="$OUT_DIR/log/${DATASET}_${EXPERIMENTBASE}_${count}_shot.log"
    EXPERIMENTNAME="${EXPERIMENTBASE}_${count}_shot"
    echo "Log file location: ${LOGFILE}"
    echo "Name of experiment: ${EXPERIMENTNAME}"

    mkdir -p $OUT_DIR/log $OUT_DIR/output $OUT_DIR/data

    python prompt_extraction/run_inference.py \
                --experiment_name $EXPERIMENTNAME \
                --doi_error_list_file $ERROR_FILE \
                --mode $DATASET \
                --out_dir $OUT_DIR \
                --prompt_index 5 \
                --debug true \
                --seed_sampling $SAMPLING \
                --seed_count $count | tee $LOGFILE
done

echo "Done"

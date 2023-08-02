#!/bin/bash
# Run 0 to 5 shots data extraction 3 times to check for reproducibility.

OUT_DIR="Run_Reprod"

# can take value Tg or bandgap
DATASET="Tg"

# SAMPLING can take the value random or error_diversity or baseline_diversity
SAMPLING="baseline_diversity"

EXPERIMENTBASE="abstr_${SAMPLING}_prompt0"

ERROR_FILE="$OUT_DIR/output/${DATASET}/llm_error_doi_list.json"
echo $EXPERIMENTBASE
echo $ERROR_FILE

start=5
end=0

mkdir -p $OUT_DIR/log $OUT_DIR/output

if [[ ! -d $OUT_DIR/data ]]; then
    echo "$OUT_DIR/data files not found"
    exit 2
fi

# Iterate over the range of numbers
for ((run=1; run<=3; run++)); do
    echo
    echo "Run: ${run}"

    # Iterate over the range of numbers
    for ((count=start; count>=end; count--)); do
        echo
        echo "Few shot count: ${count}"
        LOGFILE="$OUT_DIR/log/${DATASET}_${EXPERIMENTBASE}_run${run}_${count}shot.log"
        EXPERIMENTNAME="${EXPERIMENTBASE}_run${run}_${count}shot"

        echo "Log file location: ${LOGFILE}"
        echo "Name of experiment: ${EXPERIMENTNAME}"

        python prompt_extraction/run_inference.py \
                    --experiment_name $EXPERIMENTNAME \
                    --doi_error_list_file $ERROR_FILE \
                    --mode $DATASET \
                    --out_dir $OUT_DIR \
                    --prompt_index 0 \
                    --debug_count 30 \
                    --debug true \
                    --seed_sampling $SAMPLING \
                    --seed_count $count &> $LOGFILE
    done

    echo "Run complete: ${run}"
done

echo "Done"

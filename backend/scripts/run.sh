#!/bin/bash
# DATASET can take value Tg or bandgap, SAMPLING can take the value random or error_diversity
DATASET="Tg"
SAMPLING="random"
EXPERIMENTBASE="prompt_5_$SAMPLING"
ERROR_FILE="/data/pranav/projects/PromptExtraction/output/${DATASET}/prompt_5_0_shot/llm_error_doi_list.json"
echo $EXPERIMENTBASE
echo $ERROR_FILE
start=1
end=5

# Iterate over the range of numbers
for ((count=start; count<=end; count++)); do
    echo "Few shot count: ${count}"
    LOGFILE="/data/pranav/projects/PromptExtraction/log/log_${DATASET}_${EXPERIMENTBASE}_${count}_shot"
    EXPERIMENTNAME="${EXPERIMENTBASE}_${count}_shot"
    echo "Log file location: ${LOGFILE}"
    echo "Name of experiment: ${EXPERIMENTNAME}"
    nohup python ../PromptExtraction/run_inference.py \
                --experiment_name $EXPERIMENTNAME \
                --doi_error_list_file $ERROR_FILE \
                --mode $DATASET \
                --prompt_index 5 \
                --seed_sampling $SAMPLING \
                --seed_count $count &> $LOGFILE &
    wait
done

echo "Done"
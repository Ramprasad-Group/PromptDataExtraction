#!/bin/bash

# Set a memory threshold (in MiB)
MEM_THRESHOLD=6000  
COMMAND="python scripts/ner-filter-specific.py "
while true; do
    TOTAL_GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum}')
    TOTAL_USED_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum}')
    FREE_MEM=$((TOTAL_GPU_MEM - TOTAL_USED_MEM))

    if [ "$FREE_MEM" -gt "$MEM_THRESHOLD" ]; then
        echo "Enough GPU memory available ($FREE_MEM MiB). Running the command..."
        eval $COMMAND
        break 
    else
        echo "Not enough GPU memory available ($FREE_MEM MiB). Retrying in 30 seconds..."
        sleep 10
    fi
done

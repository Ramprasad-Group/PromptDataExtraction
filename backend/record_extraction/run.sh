#!/bin/bash

MODEL_NAME=''
MODEL_PATH=''
dataset=''
DEFAULT_TOKEN='O'
EXPT_NAME="${MODEL_NAME}_${dataset}"

python3 run_ner.py \
  --model_name_or_path $MODEL_PATH \
  --output_dir /path/to/output_dir \
  --train_file /path/to/train_file \
  --validation_file /path/to/dev_file \
  --test_file /path/to/test_file \
  --do_train \
  --do_eval \
  --do_predict \
  --use_debugpy \
  --save_strategy "epoch" \
  --cache_dir /path/to/cache_dir \
  --exp_name "$EXPT_NAME" \
  --evaluation_strategy="epoch" --overwrite_output_dir --max_seq_len 512 --num_train_epochs 7 \
  --logging_steps 2 --overwrite_cache --load_best_model_at_end \
  --metric_for_best_model f1 --save_total_limit 2

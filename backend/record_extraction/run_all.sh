ner_datasets=( "polymer_dataset" "olivetti" "ChemRxnExtractor" "berkeley" "chemdner" )

# ner_datasets=( "olivetti" )

MODEL_NAME=''
MODEL_PATH=''
DEFAULT_TOKEN="O"
# PIDS=117936
# while kill -0 $PIDS 2> /dev/null; do sleep 1; done;

for dataset in "${ner_datasets[@]}"
do
if [ "$dataset" = "olivetti" ]
then
    DEFAULT_TOKEN="null"
fi

EXPT_NAME="${MODEL_NAME}_${dataset}_7_epochs"
echo -e "\n Now training model for dataset $dataset \n"
eval "$(conda shell.bash hook)"
conda activate transformers_lm
python3 run_ner.py \
  --model_name_or_path $MODEL_PATH \
  --output_dir /path/to/$MODEL_NAME \
  --train_file /path/to/train.json \
  --validation_file /path/to/dev.json \
  --test_file /path/to/test.json \
  --do_train \
  --do_eval \
  --do_predict \
  --save_strategy "epoch" \
  --cache_dir /path/to/cache \
  --use_wandb \
  --exp_name "$EXPT_NAME" \
  --evaluation_strategy="epoch" --overwrite_output_dir --max_seq_len 512 --num_train_epochs 7 \
  --logging_steps 2 --overwrite_cache --load_best_model_at_end \
  --metric_for_best_model f1 --save_total_limit 2 \

done
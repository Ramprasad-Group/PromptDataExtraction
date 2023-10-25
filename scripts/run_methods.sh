#!/bin/bash

method_names=(
  "bandgap-gpt35-similar-full"
  "co2_perm-gpt35-similar-full"
  "cs-gpt35-similar-full"
  "ct-gpt35-similar-full"
  "dc-gpt35-similar-full"
  "density-gpt35-similar-full"
  "eab-gpt35-similar-full"
  "fs-gpt35-similar-full"
  "hardness-gpt35-similar-full"
  "h2_perm-gpt35-similar-full"
  "iec-gpt35-similar-full"
  "ionic_cond-gpt35-similar-full"
  "is-gpt35-similar-full"
  "lcst-gpt35-similar-full"
  "loi-gpt35-similar-full"
  "methanol_perm-gpt35-similar-full"
  "o2_perm-gpt35-similar-full"
  "ri-gpt35-similar-full"
  "sd-gpt35-similar-full"
  "tc-gpt35-similar-full"
  "td-gpt35-similar-full"
  "tm-gpt35-similar-full"
  "ts-gpt35-similar-full"
  "tg-gpt35-similar-full"
  "ucst-gpt35-similar-full"
  "wca-gpt35-similar-full"
  "wu-gpt35-similar-full"
  "ym-gpt35-similar-full"
)

para_subsets=(
  "bandgap_ner_full"
  "co2_perm_ner_full"
  "cs_ner_full"
  "ct_ner_full"
  "dc_ner_full"
  "density_ner_full"
  "eab_ner_full"
  "fs_ner_full"
  "hardness_ner_full"
  "h2_perm_ner_full"
  "iec_ner_ner_full"
  "ionic_cond_ner_full"
  "is_ner_full"
  "lcst_ner_full"
  "loi_ner_full"
  "methanol_perm_ner_full"
  "o2_perm_ner_full"
  "ri_ner_full"
  "sd_ner_full"
  "tc_ner_full"
  "td_ner_full"
  "tm_ner_full"
  "ts_ner_full"
  "tg_ner_full"
  "ucst_ner_full"
  "wca_ner_full"
  "wu_ner_full"
  "ym_ner_full"
)

property_names=(
  "bandgap"
  "CO2 permeability"
  "compressive strength or compressive modulus"
  "crystallization temperature or Tc"
  "dielectric constant or relative permittivity"
  "density"
  "elongation at break"
  "flexural strength or bend strength or modulus of rupture or transverse rupture strength"
  "hardness"
  "hydrogen or H2 permeability"
  "ion exchange capacity or iec"
  "proton conductivity or ionic conductivity or hydroxide conductivity or OH^{-} conductivity"
  "impact strength"
  "lower critical solution temperature"
  "limiting oxygen index"
  "methanol permeability"
  "oxygen or O2 permeability"
  "refractive index"
  "swelling degree"
  "thermal conductivity"
  "thermal decomposition temperature or thermal stability or Td"
  "melting temperature"
  "tensile strength or ultimate strength"
  "glass transition temperature or Tg"
  "upper critical solution temperature"
  "water contact angle"
  "water uptake"
  "youngs modulus"
)

nohup_folder="/data/sonakshi/PromptDataExtraction/filtered_paras/nohup/full-corpus"
chmod +w "$nohup_folder"

for i in "${!method_names[@]}"; do
    method_name="${method_names[i]}"
    filter_name="${para_subsets[i]}"
    property_name="${property_names[i]}"
    log_file="methods/${method_name}.log"
    output_file="${nohup_folder}/${method_name}.out"

    echo "Adding method: $method_name with filter: $filter_name"
    nohup python backend method new -m "$method_name" --filter "$filter_name" --dataset data1 --model gpt-3.5-turbo --api openai --info user sonakshi --info shot_selector similar --info n_shots 1 --info api_retry_delay 60 --info delay_multiplier 0.5 --info max_api_retries 1 --info api_request_delay 0.01 --info temperature 0.001 --info  prompt "Extract all $property_name values in JSONL format with 'material', 'property', 'value', 'condition' columns." --info shot_nrecords 2 --info shot_keywords false > "$output_file" 2>&1 &
done
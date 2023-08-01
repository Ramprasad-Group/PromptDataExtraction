## Files

- `bandgap_curated_data.xlsx`: Contains manually curated material names, coreferents (aliases), SMILES string, domain expert comments and bandgap values. Possibly after extraction using the BERT pipeline.

- `Tg_curated_data.xlsx`: Contains manually curated material names, coreferents (aliases), SMILES string, domain expert comments and Tg values. Possibly after extraction using the BERT pipeline.

- `Tg_extracted_data.xlsx`: Contains material names, coreferents (aliases), SMILES string, and Tg values. Possibly extracted using the BERT pipeline.

- `Polymer_solar_cell_extracted_data_curated.xlsx`: Contains solar cell related material names, coreferents (aliases), curated SMILES string, and values. Possibly after extraction using the BERT pipeline.

- `dataset_ground.json`: Contains DOI, material name, coreferents, abstract of the paper, and Tg value. Possibly manually curated.

- `dataset_nlp.json`: Similiar to the ground dataset, but generated using the BERT pipeline.

- `dataset_llm.json`: Similiar to the ground dataset, but generated using the LLM/OpenAI pipeline.

- `llm_error_doi_list.json`: A list of DOIs which failed to get processed by the LLM pipeline. Error could be due to API or JSON post-processing.

- `dataset_ground_embeddings.pt`: For each doi, relevant sentences are selected from the ground dataset, passed to the bert model and embeddings are recorded from the "last hidden state" of the outputs (pytorch tensor).

- `property_metadata.json`: Contains a list of properties, commonly used units and range of values. 

- `metrics.txt`: Output file that saves the F-1, precision, recall scores using both LLM and NLP pipeline.

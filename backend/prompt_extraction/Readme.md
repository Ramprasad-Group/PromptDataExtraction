## Input/Output

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

## Algorithms

### Run inference
The main control flow of extracting data from abstracts using LLM.

```sh
Create/load the ground dataset.
Create/load the BERT/NER dataset.
Create/load embeddings for the ground dataset.
Load the previously saved list of DOIs with errors, if any.

Create "seed message" for the prompt
    using the ground dataset, embeddings and error list.

Load any previously saved dataset of the LLM outputs.
For each of the doi,
    Get LLM response using the abstract and seed message.
    Post-process the output json to extract values.
    Add the parsed output to the LLM dataset.
Save the LLM dataset.

Compute metrics using the ground and LLM dataset.
    Create the list of dois that has errors.

Compute metrics using the ground and BERT/NER dataset.
Save the metrics and stats.
```

### Create Dataset
Pre-process the manually created and NER based dataset to compare against the LLM extracted data.

```sh
Set the Tg curated excel location.
Set the Bg curated excel location.
Set the Tg nlp extracted csv location.
Set the Bg nlp extracted csv location.

# This includes both curated and extracted items.
Set the polymer solar cell excel location.

Setup MongoDB connecton.
Get the 'modular run 4' collection from the DB.

Load the curated dataset as ground truth.
Load the nlp csv as nlp dataset.

# Ground dataset: dict[doi] = [records...]
For each row in the curated excel that has curated=1,
    Get the abstract from the DB collection as text.
    Post-process the text to make sure its a string.
    Get the material, coreferent, property values from the row.
    Add all the values to the records.
    Add the records to the ground dataset dois list.
    If doi already added to the dataset list,
        set empty text.

# NLP dataset: dict[doi] = [records...]
For each row in the nlp csv,
    Get the material, coreferent, property values from the row.
    Add all the values to the records.
    Add the records to the nlp dataset dois list.

Print number of dois and records in the ground dataset.
Return the ground and the nlp dataset.
```

### Seed Prompt
Create n-shot examples based on different methods.

```sh
Use one of the methods below to create {doi: abstract}.
Create a shot/prompt based on the abstract, material and properties.
    Use json dumps.
Return the shot/prompt, list of doi

clustering:
    # The goal is to choose the most diverse DOIs.
    Construct K independent clusters based on the embeddings
        using the K-means clustering.
    Return the <=K DOIs that sits at the center of the clusters.

minimum:
    Find minimum N number of items from the dataset
        those have atleast M records.
    Return {doi: abstract} for the selected dois.

random:
    Find random N number of items from the dataset
        those have atleast M records.
    Return {doi: abstract} for the selected dois.

baseline_diversity:
    Use clustering to choose N dois.
    Return {doi: abstract} for the selected dois.

error_diversity:
    Select the dois that had errors.
    Use clustering to choose N dois from the selected dois.
    Return {doi: abstract} for the selected dois.
```

### Compute Metrics
Calculate metrics to compares LLM extracted dataset.

```sh
For each ground truth doi and list of items,
    Get the material, coreferents, property values
        for each of the extracted item.
    Normalize the extracted property values.
    Check if property value and material names match.
        Use a fuzzy comparison.
    If no extracted item for the property,
        mark as false negative.
    If no values were extracted for the doi,
        mark as false negative.

For each extracted doi and list of items,
    Add to error list if property value not a string.

    # Not sure how this is false positive.
    If property value is None or NA,
        mark as false positive.

    Check against the records of the ground truth items.
        If property value not in ground truth items,
            mark as false positive.

Calculate and return precision, recall, f1 and error list.
```

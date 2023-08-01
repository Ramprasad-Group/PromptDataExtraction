import os
import json
import spacy
import torch
from transformers import AutoTokenizer, AutoModel

import config

class ComputeEmbeddings:
    def __init__(self):
        property_metadata_file = config.DATA_DIR + '/data/property_metadata.json'
        with open(property_metadata_file, 'r') as f:
            self.property_metadata = json.load(f)

        # self.property_metadata = json.load(open('property_metadata.json', 'r'))
        model_location = 'models/MaterialsBERT'
        self.tokenizer = AutoTokenizer.from_pretrained(model_location)
        self.model = AutoModel.from_pretrained(model_location)

    
    def run(self, doi_dict, property_name):
        """Compute embeddings for the given DOI dict"""
        embedding_dict = dict()
        for doi, items in doi_dict.items():
            text = items[0]['abstract']
            material_coreferents = []
            for item in items:
                material_coreferents.extend(item['material_coreferents'])

            relevant_sentences = self.compute_relevant_sentences(text, material_coreferents, property_name)
            embeddings = self.compute_embeddings(relevant_sentences)
            embedding_dict[doi] = embeddings
        
        return embedding_dict

    def compute_relevant_sentences(self, text, material_coreferents, property_name) -> str:
        """Compute the relevant sentences for the given text"""
        # Here we simply check for the presence of the keyword in the text, we can also check for the presence of the material entity
        nlp = spacy.load("en_core_web_sm")
        spacy_doc = nlp(text)
        relevant_sentences = []
        property_name_map = {
            'Tg': 'glass transition temperature',
            'bandgap': 'bandgap',
            'PCE': 'power conversion efficiency',
            'Voc': 'voltage',
            'Jsc': 'current',
            'FF': 'fill factor'
        }
        property_name_mapped = property_name_map[property_name]

        property_coreferents = self.property_metadata[property_name_mapped]['property_list']
        for sentence in spacy_doc.sents:
            if any([coreferent in sentence.text for coreferent in property_coreferents]) or any([material in sentence.text for material in material_coreferents]):
                relevant_sentences.append(sentence.text)

        return " ".join(relevant_sentences)

    def compute_embeddings(self, text):
        """Compute the embeddings for the given text"""
        # Tokenize the sentences
        encoded_inputs = self.tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors='pt')

        # Obtain the embeddings from the model
        with torch.no_grad(): # There may be more ways to do this, can use the CLS token embedding as well
            outputs = self.model(**encoded_inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze(0)

        return embeddings

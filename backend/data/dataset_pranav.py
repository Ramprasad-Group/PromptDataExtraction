import ast
import pandas as pd
from collections import defaultdict

import sett
from . import mongodb

import pylogg
log = pylogg.New('dataset')


class GroundDataset:
    def __init__(self):
        """Create dataset for zero shot inference"""
        # Setup database connection
        self.db = mongodb.connect()
        self.collection = self.db[sett.PEAbstract.mongodb_collection]
    
    def create_dataset(self,  mode='Tg'):
        """Create dataset for downstream zero shot inference"""
        # negative_DOI_dict = dict()
        assert mode in ['Tg', 'bandgap', 'PSC']

        if mode=='Tg':
            df_ground = pd.read_excel(sett.Dataset.tg_ground_xl, keep_default_na=False)
            df_nlp = pd.read_csv(sett.Dataset.tg_extracted_csv, keep_default_na=False)
            property_name = 'glass transition temperature'

        elif mode=='bandgap':
            df_ground = pd.read_excel(sett.Dataset.bandgap_ground_xl, keep_default_na=False)
            df_nlp = pd.read_csv(sett.Dataset.bandgap_extracted_csv, keep_default_na=False)
            property_name = 'bandgap'

        # df_PSC = pd.read_excel(self.PSC_dataset_location, keep_default_na=False)
        output_dataset_nlp = defaultdict(list)
        output_dataset_ground = defaultdict(list)
        for index, row in df_ground.iterrows():
            doi = row['DOI']
            if row['curated']==1:
                if doi not in output_dataset_ground:
                    text = self.collection.find_one({'DOI': doi})['abstract']
                    text = self._text_postprocessing(text)
                else:
                    text = ''
                output_dataset_ground[doi].append({'material': row['material'],
                                            'material_coreferents': self._process_entity_coreferents(row),
                                            'abstract': text,
                                            'property_value': str(row[property_name]),})
        
        for index, row in df_nlp.iterrows():
            doi = row['DOI']
            if doi in output_dataset_ground:
                output_dataset_nlp[doi].append({'material': row['material'],
                                            'material_coreferents': self._process_entity_coreferents(row),
                                            'property_value': row[property_name].replace('="', '').replace('"', ''),})
        
        log.info(f'Number of DOI\'s in dataset: {len(output_dataset_ground)}')
        log.info(f'Number of records in dataset: {sum([len(item_list) for item_list in output_dataset_ground.values()])}')
        return output_dataset_ground, output_dataset_nlp

    def _process_entity_coreferents(self, row):
        """Process the entity coreferents to get a list of entities"""
        if row['material_coreferents']:
            coreferents = ast.literal_eval(row['material_coreferents'])
        else:
            coreferents = [row['material']]
        if not coreferents:
            coreferents = [row['material']]
        
        return coreferents
    
    def _text_postprocessing(self, text):
        if type(text) == list:
            text = text[0]
        elif type(text) == str:
            pass
        else:
            text = ''
        
        return text

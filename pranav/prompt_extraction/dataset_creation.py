"""Create initial dataset for zero shot inference"""

# Load Tg dataset, use labeled data to create a new dataset and pull up other random DOI's that don't have Tg data by unbalanced sampling

# use ground truth labels in the known dataset

import pandas as pd
from collections import defaultdict
import ast

import debugpy
import argparse

from prompt_extraction import utils

import config

parser = argparse.ArgumentParser()

parser.add_argument(
    "--use_debugpy",
    help="Use remote debugging",
    action="store_true",
)
import logging
logger = logging.getLogger()
# logging.basicConfig()

class DatasetCreation:
    def __init__(self):
        """Create dataset for zero shot inference"""
        self.Tg_dataset_location = config.DATA_DIR+'/data/glass_transition_temperature/glass_transition_temperature_curated_data.xlsx'
        self.Tg_nlp_extracted_dataset_location = config.DATA_DIR+'/data/glass_transition_temperature/glass_transition_temperature_extracted_data.csv'
        
        self.bandgap_dataset_location = config.DATA_DIR+'/data/bandgap/bandgap_curated_data.xlsx'
        self.bandgap_nlp_extracted_dataset_location = config.DATA_DIR+'/data/bandgap/bandgap_extracted_data.csv'
        
        self.PSC_dataset_location = config.DATA_DIR+'/data/polymer_solar_cells/polymer_solar_cell_extracted_data_curated.xlsx'
        # Setup database connection
        self.setup_connection()
    
    def setup_connection(self):
        self.db = utils.connect_remote_database()
        self.collection = self.db['modular_run_4']
    
    def process_entity_coreferents(self, row):
        """Process the entity coreferents to get a list of entities"""
        if row['material_coreferents']:
            coreferents = ast.literal_eval(row['material_coreferents'])
        else:
            coreferents = [row['material']]
        if not coreferents:
            coreferents = [row['material']]
        
        return coreferents
    
    def create_dataset(self,  mode='Tg'):
        """Create dataset for downstream zero shot inference"""
        # negative_DOI_dict = dict()
        assert mode in ['Tg', 'bandgap', 'PSC']
        if mode=='Tg':
            df_ground = pd.read_excel(self.Tg_dataset_location, keep_default_na=False)
            df_nlp = pd.read_csv(self.Tg_nlp_extracted_dataset_location, keep_default_na=False)
            property_name = 'glass transition temperature'
        elif mode=='bandgap':
            df_ground = pd.read_excel(self.bandgap_dataset_location, keep_default_na=False)
            df_nlp = pd.read_csv(self.bandgap_nlp_extracted_dataset_location, keep_default_na=False)
            property_name = 'bandgap'

        # df_PSC = pd.read_excel(self.PSC_dataset_location, keep_default_na=False)
        output_dataset_nlp = defaultdict(list)
        output_dataset_ground = defaultdict(list)
        for index, row in df_ground.iterrows():
            doi = row['DOI']
            if row['curated']==1:
                if doi not in output_dataset_ground:
                    text = self.collection.find_one({'DOI': doi})['abstract']
                    text = self.text_postprocessing(text)
                else:
                    text = ''
                output_dataset_ground[doi].append({'material': row['material'],
                                            'material_coreferents': self.process_entity_coreferents(row),
                                            'abstract': text,
                                            'property_value': str(row[property_name]),})
        
        for index, row in df_nlp.iterrows():
            doi = row['DOI']
            if doi in output_dataset_ground:
                output_dataset_nlp[doi].append({'material': row['material'],
                                            'material_coreferents': self.process_entity_coreferents(row),
                                            'property_value': row[property_name].replace('="', '').replace('"', ''),})
        
        self.dataset_statistics(output_dataset_ground)
        
        return output_dataset_ground, output_dataset_nlp

    def text_postprocessing(self, text):
        if type(text) == list:
            text = text[0]
        elif type(text) == str:
            pass
        else:
            text = ''
        
        return text

    def dataset_statistics(self, output_dataset):
        """Get dataset statistics"""
        logger.info(f'Number of DOI\'s in dataset: {len(output_dataset)}')
        logger.info(f'Number of records in dataset: {sum([len(item_list) for item_list in output_dataset.values()])}')
        

if __name__ == '__main__':
    args = parser.parse_args()
    if args.use_debugpy:
        debugpy.listen(5678)
        debugpy.wait_for_client()
        debugpy.breakpoint()
    dataset_creation = DatasetCreation()
    output_dataset, negative_doi_list = dataset_creation.create_dataset()

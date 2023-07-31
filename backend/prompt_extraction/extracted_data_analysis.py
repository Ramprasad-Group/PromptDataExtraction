# Analyze the data extracted from the body of papers

# create plots for previous pipeline extracted data and new pipeline extracted data

# have a bandgap mode and Tg mode

from PromptExtraction.utils import connect_remote_database, config_plots
from PromptExtraction.full_text_extraction import FullTextExtraction

from record_extraction_pipeline.base_classes import PropertyValuePair
from record_extraction_pipeline.property_extraction import PropertyExtractor

import matplotlib.pyplot as plt

import matplotlib as mpl
mpl.use('Cairo')
config_plots(mpl)

import argparse
from dataclasses import dataclass
import debugpy

from typing import List
from os import path

import config

parser = argparse.ArgumentParser()

parser.add_argument(
    "--use_debugpy",
    help="Use remote debugging",
    action="store_true",
)

parser.add_argument(
    "--collection_name",
    help="Name of collection to use as input",
    type=str,
    default='full_text_data'
)

parser.add_argument(
    "--mode",
    help="Mode in which to run the code. Use Tg or bandgap",
    type=str,
    default='Tg'
)

parser.add_argument(
    "--top_k",
    help="Top k values to print and output",
    type=int,
    default=5
)

class AnalyzeData(FullTextExtraction):
    def __init__(self, args) -> None:
        super(AnalyzeData, self).__init__(args=args)
        self.args = args
        if args.mode=='Tg':
            self.min_value = -100
            self.max_value = 450
            self.unit = '°C'
            self.ylim = 6500
        elif args.mode=='bandgap':
            self.min_value = 0
            self.max_value = 7
            self.unit = 'eV'
            self.ylim = 2500
        # Connect to the database
        self.setup_connection()
        self.property_extractor = PropertyExtractor()
        self.output_dir = f'/data/pranav/projects/PromptExtraction/output/{args.mode}'
        # property_metadata_file = '/data/pranav/projects/PromptExtraction/data/property_metadata.json'
        # with open(property_metadata_file, 'r') as f:
        #     self.metadata = json.load(f)
        # self.map_dict = {'Tg': 'glass transition temperature', 'bandgap': 'bandgap'}

    def setup_connection(self) -> None:
        self.db = connect_remote_database()
        self.collection = self.db[self.args.collection_name]
    
    def abstract_data_statistics(self, collection) -> None:
        # Iterate over the data and count the number of data points and abstracts containing a certain property
        property_list = self.metadata[self.args.mode]['coreferents']
        print(f'Property list: {property_list}')
        cursor = collection.find({'material_records.property_record.entity_name': {'$in': property_list}})
        property_count = 0
        abstract_count = 0
        for doc in cursor:
            abstract_status = False
            for record in doc.get('material_records', []):
                if record.get('property_record', {}).get('entity_name', '') in property_list and record.get('material_name', []):
                    property_count += 1
                    abstract_status = True
            if abstract_status:
                abstract_count += 1
        
        print(f'Number of abstracts with {self.args.mode} data: {abstract_count}')
        print(f'Number of data points in abstracts with {self.args.mode} data: {property_count}')


    def iterate_over_data(self) -> None:
        # Iterate over the data and create the data in a certain format in a data structure
        cursor = self.collection.find({})
        nlp_extracted_data = []
        llm_extracted_data = []
        missed_count = 0
        total_paras = 0
        bert_missed_count = 0
        total_docs = 0
        relevant_docs = 0
        relevant_paras = 0

        
        for doc in cursor:
            doi = doc['DOI']
            total_docs += 1
            relevant_status = False
            for para_records in doc['paragraph_records']:
                if 'BERT_pipeline' in para_records:
                    if 'material_records' in para_records['BERT_pipeline']:
                        for record in para_records['BERT_pipeline']['material_records']:
                            if 'material_name' in record and len(record['material_name'])>=1:
                                if 'property_record' in record and record['property_record']['entity_name'] in self.metadata[self.args.mode]['coreferents']:
                                    property_value_pair = PropertyValuePairLocal(
                                                                            doi=doi,
                                                                            material_name=record['material_name'][0]['entity_name'],
                                                                            property_value=record['property_record']['property_value'],
                                                                            entity_name=record['property_record']['entity_name'],
                                                                            property_numeric_value=record['property_record']['property_numeric_value'],
                                                                            property_unit=record['property_record']['property_unit']
                                                                            )
                                    # self.property_extractor.single_property_entity_postprocessing(property_value_pair)
                                    nlp_extracted_data.append(property_value_pair)
                else:
                    bert_missed_count += 1

                total_paras += 1
                if self.args.mode in para_records:
                    relevant_para_status = False
                    for material_name, property_value in self.llm_records_iterator(para_records[self.args.mode]): # Need to write an iterator for this to handle all possible cases
                        relevant_status = True
                        property_value_pair = PropertyValuePairLocal(doi=doi, material_name=material_name, property_value=property_value, entity_name=self.args.mode)
                        self.property_extractor.single_property_entity_postprocessing(property_value_pair)
                        llm_extracted_data.append(property_value_pair)
                        relevant_para_status = True
                    if relevant_para_status:
                        relevant_paras += 1
                else:
                    missed_count += 1

            if relevant_status:
                relevant_docs += 1
        
        print(f'Number of paragraphs which need not have been sent to LLM for {self.args.mode}: {missed_count} out of {total_paras}')
        print(f'Number of paragraphs which did not have property values detected by BERT for {self.args.mode}: {bert_missed_count} out of {total_paras}')
        print(f'Number of documents which have relevant paragraphs for {self.args.mode}: {relevant_docs} out of {total_docs}')
        print(f'Number of relevant paragraphs for {self.args.mode}: {relevant_paras} out of {total_paras}')
        
        return nlp_extracted_data, llm_extracted_data

    def llm_records_iterator(self, prop_records_list):
        """Iterate over the records extracted using LLMs"""
        property_null_list = ['n/a', 'not mentioned', 'not found', 'not specified', 'not provided', 'unknown', 'no']
        for item in prop_records_list:
            if type(item)!=dict:
                continue
            material_name = item.get('material', '')
            property_value = item.get('property_value', '')
            if material_name and property_value:
                if type(property_value)==str and not any([kwd in property_value.lower() for kwd in property_null_list]):
                    yield material_name, property_value
                elif type(property_value)==float or type(property_value)==int:
                    yield material_name, str(property_value)
                elif type(property_value)==dict:
                    for _, value in property_value.items():
                        if value and type(value)==str and not any([kwd in value.lower() for kwd in property_null_list]):
                            yield material_name, value
                elif type(property_value)==list:
                    for value in property_value:
                        if value and type(value)==str and not any([kwd in value.lower() for kwd in property_null_list]):
                            yield material_name, value
                

    def _make_plots_(self, extracted_data: List[PropertyValuePair], type: str) -> None:
        assert type in ['llm', 'bert']
        # Create histogram of NLP extracted and LLM extracted data
        property_values = [record.property_numeric_value for record in extracted_data if record.property_numeric_value!= '' and record.property_numeric_value<self.max_value and record.property_numeric_value>self.min_value]
        print(f'Number of records with property values for {self.args.mode} and {type}: {len(property_values)}')
        fig, ax = plt.subplots(figsize=(10,10))
        ax.hist(property_values, bins=100)
        ax.set_xlabel(f'{self.args.mode} ({self.unit})')
        ax.set_ylabel('Frequency')
        ax.set_ylim(0, self.ylim)
        ax.set_title(f'{self.args.mode} {type} extracted data histogram')
        ax.set_xticks(ax.get_xticks()[::2]) # Display only every 3rd tick

        fig.savefig(path.join(self.output_dir, f'{self.args.mode}_{type}_histogram.png'))
    
    def find_max_entries(self, extracted_data: List[PropertyValuePair]) -> None:
        """Find the entries with the maximum property values"""
        # Sort the data by property value and find the top k entries
        # Filter out the entries with None property values
        filtered_data = [item for item in extracted_data if item.property_numeric_value!='' and item.property_numeric_value<self.max_value and item.property_numeric_value>self.min_value]
        sorted_data = sorted(filtered_data, key=lambda x: x.property_numeric_value, reverse=True) # This can be slow
        truncated_data = [{'doi': item.doi, 'material': item.material_name, 'property_value': item.property_value} for item in sorted_data[:self.args.top_k]]
        return truncated_data

    def run(self) -> None:
        # Iterate over the data and create the data in a certain format in a data structure
        collection = self.db['modular_run_4']
        self.abstract_data_statistics(collection)
        nlp_extracted_data, llm_extracted_data = self.iterate_over_data()
        # Create histogram of NLP extracted and LLM extracted data
        if llm_extracted_data:
            self._make_plots_(llm_extracted_data, type='llm')
            max_reported_values_llm = self.find_max_entries(llm_extracted_data)
            print(f'Highest reported values using LLMs: {max_reported_values_llm}')
        if nlp_extracted_data:
            self._make_plots_(nlp_extracted_data, type='bert')
            max_reported_values_nlp = self.find_max_entries(nlp_extracted_data)
            print(f'Highest reported values using NLP: {max_reported_values_nlp}')

@dataclass
class PropertyValuePairLocal(PropertyValuePair):
    doi: str = ''

if __name__ == "__main__":
    args = parser.parse_args()
    if args.use_debugpy:
        debugpy.listen(5678)
        debugpy.wait_for_client()
        debugpy.breakpoint()
    data_analyzer = AnalyzeData(args)
    data_analyzer.run()
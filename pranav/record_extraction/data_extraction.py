from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

import record_extractor
import utils as record_extractor_utils
from utils import LoadNormalizationDataset
from base_classes import GROUPED_SPAN_COLUMNS

import torch
import traceback
import argparse
import logging
import time


parser = argparse.ArgumentParser()
parser.add_argument(
    "--db_local",
    dest="db_local",
    help="True if the database to be accessed is on the same server as the server on which code is running",
    action="store_true",
)

parser.add_argument(
    "--skip_n",
    dest="skip_n",
    help="Skip the first n records output from the find query",
    type=int,
    default=0
)

parser.add_argument(
    "--cap_docs",
    dest="cap_docs",
    help="Maximum number of documents to iterate over while extracting data",
    type=int,
    default=5000
)

parser.add_argument(
    "--delete_collection",
    dest="delete_collection",
    help="True to delete any preexisting collection with the same name. False to continue adding documents to that database",
    action="store_true"
)

parser.add_argument(
    "--check_repeat_doi",
    dest="check_repeat_doi",
    help="Check if the same DOI already exists in the database",
    action="store_true"
)

parser.add_argument(
    "--collection_output_name",
    dest="collection_output_name",
    help="Name of output collection to save the data to",
    default='data_test_run'
)

parser.add_argument(
    "--use_debugpy",
    help="Use remote debugging",
    action="store_true",
)

parser.add_argument(
    "--verbose",
    help="Store verbose output of material_entities, group_tokens and property spans",
    action="store_true",
)

parser.add_argument(
    "--polymer_filter",
    help="Restrict extraction of data to polymer papers, the negation will look at all other papers",
    action="store_true",
)

class ScaleExtraction:
    def __init__(self, query, collection_output_name=None, skip_n=0, cap_docs=None, delete_collection=False, check_repeat_doi=False, debug=False, verbose=True, polymer_filter=True):
        self.collection_output_name = collection_output_name
        self.query = query
        self.debug = debug
        self.skip_n = skip_n
        self.verbose = verbose
        self.polymer_filter = polymer_filter
        self.delete_collection = delete_collection
        self.check_repeat_doi = check_repeat_doi
        self.timer = {'abstract_preprocessing': [], 'ner': [], 'relation_extraction': []}
        if cap_docs:
            self.cap_docs = int(cap_docs)
        else:
            self.cap_docs = cap_docs
        if torch.cuda.is_available():
            print('GPU device found')
            self.device = 1
        else:
            self.device = -1
        if not self.debug:
            self.logger = logging.getlogger(__name__)
        else:
            self.logger = None
        model_file = '' # Location of BERT encoder model file to load

        # Load NormalizationDataset used to normalize polymer names
        normalization_dataloader = LoadNormalizationDataset()
        self.train_data = normalization_dataloader.process_normalization_files()

        tokenizer = AutoTokenizer.from_pretrained(model_file, model_max_length=512)
        model = AutoModelForTokenClassification.from_pretrained(model_file)
        # Load model and tokenizer
        self.ner_pipeline = pipeline(task="ner", model=model, tokenizer=tokenizer, grouped_entities=True, device=self.device)

    def setup_connection(self):
        """Setup connection to a database that has stored documents. Not implemented here"""
        
        self.server = None
        self.db = None
        self.collection_input = None
        if self.collection_output_name:
            self.collection_output = self.db[self.collection_output_name]
        
    
    def scale_data_collection(self):
        """Scale data collection over entire dataset"""
        docs_parsed = self.skip_n
        self.setup_connection()
        num_docs = self.collection_input.count_documents(self.query)
        print(f'Number of documents returned by query: {num_docs}')
        if self.delete_collection:
            self.db.drop_collection(self.collection_output)
            print(f'Deleting collection of name {self.collection_output_name}')
        cursor = self.collection_input.find(self.query).skip(self.skip_n)
        if self.collection_output_name:
            abstracts_with_data = self.collection_output.count_documents({})
        else:
            abstracts_with_data = 0
        if not self.debug:
            start_time = time.time()
            self.logger.warning(f'Start time = {start_time}')
        while docs_parsed < num_docs:
            with cursor:
                try:
                    for i, doc in enumerate(cursor):
                
                        doi = doc.get('DOI')
                        if self.check_repeat_doi and self.collection_output.find_one({'DOI': doi}):
                            continue
                        output = {}
                        docs_parsed+=1
                        begin = time.time()
                        abstract = doc['abstract']
                        self.timer['abstract_preprocessing'].append(time.time()-begin)
                        # Pre process abstract
                        begin = time.time()
                        ner_output = self.ner_pipeline(abstract, truncation=True, max_length=512)
                        self.timer['ner'].append(time.time()-begin)
                        if self.debug:
                            self.ner_output = ner_output
                            self.text = abstract
                        # In case there are no predicted tokens, we continue to the next document
                        if not ner_output: continue
                        record_extraction_input = record_extractor_utils.ner_feed(ner_output, abstract)
                        # Pass logger
                        relation_extractor = record_extractor.RelationExtraction(text=abstract, spans=record_extraction_input, normalization_dataset=self.train_data, polymer_filter=self.polymer_filter, logger=self.logger, verbose=self.verbose)
                        try:
                            begin = time.time()
                            output, _ = relation_extractor.process_document()
                            if output:
                                self.timer['relation_extraction'].append(time.time()-begin)
                        except Exception as e:
                            if not self.debug:
                                self.logger.warning(f'Exception {e} occurred for doi {doi} while parsing the input\n')
                                self.logger.exception(e)
                            else:
                                print(f'Exception {e} occurred for doi {doi} while parsing the input\n')
                                print(traceback.format_exc())
                                self.relation_extractor = relation_extractor
                        if docs_parsed%500==0:
                            if self.logger:
                                self.logger.warning('\n')
                                self.logger.warning(f'Done with {docs_parsed} documents\n')
                                self.logger.warning(f'Abstracts with data: {abstracts_with_data} documents\n')
                                self.logger.warning(f'Positivity ratio: {float(abstracts_with_data/docs_parsed):.2f}\n')
                            else:
                                print(f'\nDone with {docs_parsed} documents\n')

                        # Log some metrics when applying model at scale
                        if output:
                            abstracts_with_data+=1
                            output['DOI'] = doi
                            output['title'] = doc.get('title')
                            output['abstract'] = abstract
                            output['year'] = doc.get('year', 0) # Default values in case one is not found
                            output['month'] = doc.get('month', 0)
                            output['day'] = doc.get('day', 0)
                            if self.verbose:
                                output['material_mentions'] = relation_extractor.material_entity_processor.material_mentions.return_list_dict()
                                output['grouped_spans'] = [named_tuple_to_dict(span) for span in relation_extractor.material_entity_processor.grouped_spans]
                            # Insert output to collection
                            if not self.debug:
                                self.collection_output.insert_one(output)
                            else:
                                print(output)
                                self.relation_extractor = relation_extractor
                        if self.cap_docs and i>self.cap_docs: break

                except Exception as e:
                    if self.logger:
                        self.logger.warning(f'Exception {e} occurred for doi {doi} while iterating over cursor\n')
                        self.logger.exception(e)
                    else:
                        print(f'Exception {e} occurred for doi {doi} in outer loop\n')
        
            if hasattr(self, 'server'): self.server.stop()

            if docs_parsed < num_docs:
                if self.logger: self.logger.warning(f'Setting up SSH and database connection again \n')
                self.setup_connection()
                cursor = self.collection_input.find(self.query).skip(docs_parsed)
        
        if not self.debug:
            end_time = time.time()
            self.logger.warning(f'End time = {end_time}')
            self.logger.warning(f'Time taken = {end_time-start_time} seconds')
            self.logger.warning(f'Documents parsed = {docs_parsed}')

def named_tuple_to_dict(named_tuple):
    current_dict = {}
    for col in GROUPED_SPAN_COLUMNS:
        current_dict[col] = getattr(named_tuple, col)
    
    return current_dict

if __name__ == '__main__':
    args = parser.parse_args()
    if args.polymer_filter:
        query = {'abstract': {'$regex': 'poly', '$options': 'i'}}
    else:
        query = {'$and': [{'abstract': {'$not': {'$regex': 'poly', '$options': 'i'}}}, {'abstract': {'$exists': True}}, {'abstract': {'$ne': None}}]}
    scale_extractor = ScaleExtraction(query = query, collection_output_name=args.collection_output_name, db_local=args.db_local, skip_n = args.skip_n, cap_docs=args.cap_docs, delete_collection=args.delete_collection, check_repeat_doi=args.check_repeat_doi, debug=False, verbose=args.verbose, polymer_filter=args.polymer_filter)
    scale_extractor.scale_data_collection()
import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
logger = logging.getLogger()

import config
from PromptExtraction.run_inference import RunInformationExtraction
from PromptExtraction.parse_args import parse_args
from PromptExtraction.utils import connect_remote_database, LoadNormalizationDataset, ner_feed
from PromptExtraction.pre_processing import PreProcessor

from record_extraction import record_extractor

import sys
import debugpy
import openai

from collections import defaultdict

import json

# from os import path

# import time

import torch

from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline


# logger.setLevel(logging.INFO)

openai.api_key = config.API_KEY

class FullTextExtraction(RunInformationExtraction):
    def __init__(self, args):
        super(FullTextExtraction, self).__init__(args=args)
        self.skip_headers = ['related', 'supporting information', 'request username', 'password changed successfully',
                             'information', 'figures', 'acknowledgements', 'acknowledgement', 'terms & conditions',
                             'conflict of interest', 'conflicts of interest', 'supporting information available', 'notes',
                             'declaration of interest', 'rights and permissions', 'about this article', 'references',
                             'references and notes', 'author information', 'additional information', 'funding sources',
                             'credit authorship contribution statement', 'funding', 'fundings', 'declaration of conflicting interests',
                             'competing interests', 'conflict-of-interest disclosure', 'authorship contribution statement',
                             'authorship', 'authorship contributions and disclosure of conflicts of interest',
                             'abbreviations', 'availability of supporting data', 'funding information', 'authorship statement',
                             'author statement', 'disclosures', 'disclosure of potential conflicts of interest',
                             'statement of conflicts', 'statement of conflict of interest', 'uncited references',
                             'electronic supplementary material', 'ethics declarations', 'copyright', 'author contributions',
                             'supplementary materials', 'supplementary data', 'supplementary files', 'appendix a. supplementary data',
                             'supplementary information', 'authors contribution', 'conflict of interest statement',
                             'disclosure', 'financial interest']

        # Have a debug mode that counts tokens and does not pass them to OpenAI API in order to estimate cost
        self.query = {'$and':[{'abstract': {'$regex': 'poly', '$options': 'i'}},
                             {'full_text': {'$exists': True}}
                             ]}
        self.metadata = {'Tg':{'ground_truth_data': f'/data/pranav/projects/PromptExtraction/output/Tg/dataset_ground.json',
                                'coreferents': ['Tg', 'T_{g}', 'T g', 'T_{g})', "T_{g} 's", 'glass transition', 'glass transitions', 'glass transition temperature', 'glass transition temperatures', 'glass transition temperatures', 'T_{g}s', 'glass-transition temperatures'],
                                'DOI_list': ['10.1002/pola.1179', '10.1002/app.34170'],
                                'unit_list': ['K', '° C', '°C']
                                },
                        'bandgap':{'ground_truth_data': f'/data/pranav/projects/PromptExtraction/output/bandgap/dataset_ground.json',
                                   'coreferents': ['bandgap', 'band gap', 'band-gap', 'band-gaps', 'bandgaps', 'band gaps', 'E_{g}', 'optical bandgap', 'optical band gap', 'optical band gaps', 'optical bandgaps', 'bandgap energies', 'optical energy bandgaps', 'optical energy gap', 'energy bandgap', 'optical band-gaps', 'optical-band-gap energies', 'optical band-gap', 'optical band gap energy', 'band gap energies', 'band gap energy', 'electrochemical band gap', 'electrochemical band gaps', 'Eg'],
                                   'DOI_list': ['10.1039/c8nj04453h', '10.1021/cm202247a', '10.1016/j.eurpolymj.2014.07.006'],
                                   'unit_list': ['eV']
                                }
                        }
        self.material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC']

        self.filtration_dict = defaultdict(int)

        # Load NER model
        if torch.cuda.is_available():
            logger.info('GPU device found')
            self.device = 1
        else:
            self.device = -1
        
        normalization_dataloader = LoadNormalizationDataset()
        self.train_data, self.test_data = normalization_dataloader.process_normalization_files()
        model_file = '/data/pranav/projects/polymer_ner/data/polymer_dataset_labeling_6/output/MaterialsBERT/'
        self.tokenizer = AutoTokenizer.from_pretrained(model_file, model_max_length=512)
        model = AutoModelForTokenClassification.from_pretrained(model_file)
        # Load model and tokenizer
        self.ner_pipeline = pipeline(task="ner", model=model, tokenizer=self.tokenizer, aggregation_strategy="simple", device=self.device)

        self.pre_processor = PreProcessor()

        self.token_cost = 0.002/1000 # Cost per token in dollars

        self.generation_constant = 30 # Assume 30 tokens are generated on average per prompt

        self.setup_connection()

        # Initialize output database to save the result of the extraction, have db schema be close to abstract db schema
    
    def setup_connection(self):
        self.db = connect_remote_database()
        self.collection_input = self.db['polymer_DOI_records_prod']

        if self.args.collection_output_name:
            self.collection_output = self.db[self.args.collection_output_name]

    
    def run_inference(self):
        """Run the full text extraction model on the input text"""
        num_docs = self.collection_input.count_documents(self.query)
        # Run a query over all the paragraphs in the text
        logger.info(f'Number of documents returned by query: {num_docs}')
        cursor = self.collection_input.find(self.query, no_cursor_timeout=True).skip(self.args.skip_n)
        if self.args.delete_collection:
            self.db.drop_collection(self.args.collection_output_name)
        docs_parsed = self.args.skip_n
        relevant_paras = 0
        seed_prompt_Tg, token_count_Tg = self.seed_construction('Tg')
        seed_prompt_bandgap, token_count_bandgap = self.seed_construction('bandgap')
        while docs_parsed < num_docs:
            with cursor:
                try:
                    for i, doc in enumerate(cursor):
                        doi = doc.get('DOI')
                        docs_parsed+=1
                        if self.collection_output.find_one({'DOI': doi}):
                            continue
                        output = {}
                        output['DOI'] = doi
                        output['journal'] = doc.get('journal')
                        output['title'] = doc.get('title')
                        output['year'] = doc.get('year')
                        output['paragraph_records'] = []
                        self.filtration_dict['total_docs']+=1

                        if docs_parsed%10000==0:
                            logger.info(f'Number of documents parsed: {docs_parsed}')

                        if self.args.debug and relevant_paras>self.args.debug_count:
                            break
                        
                        for para, section_name in self.para_generator(doc['full_text'], para_name='main_body'):
                            if not para:
                                continue
                            self.filtration_dict['total_paragraphs']+=1
                            para = self.pre_processor.pre_process(para)
                            Tg_output, output_para, ner_output = self.process_property(mode='Tg', para=para, seed_prompt=seed_prompt_Tg, token_count=token_count_Tg, doi=doi)
                            bandgap_output, output_para, _ = self.process_property(mode='bandgap', para=para, seed_prompt=seed_prompt_bandgap, token_count=token_count_bandgap, doi=doi, ner_output=ner_output, output_bert=output_para)
                            
                            if bandgap_output or Tg_output or output_para:
                                output['paragraph_records'].append({'section_name': section_name, 'paragraph': para})
                                relevant_paras+=1

                            if bandgap_output:
                                output['paragraph_records'][-1]['bandgap'] = bandgap_output
                            if Tg_output:
                                output['paragraph_records'][-1]['Tg'] = Tg_output
                            if output_para:
                                output['paragraph_records'][-1]['BERT_pipeline'] = output_para
                        
                        if output['paragraph_records']:
                            if any(['bandgap' in para_dict for para_dict in output['paragraph_records']]):
                                self.filtration_dict['bandgap_documents']+=1
                            if any(['Tg' in para_dict for para_dict in output['paragraph_records']]):
                                self.filtration_dict['Tg_documents']+=1

                            self.filtration_dict['relevant_documents']+=1
                            self.collection_output.insert_one(output)


                except Exception as e:
                    logger.warning(f'Exception {e} occurred for doi {doi} while iterating over cursor\n')
                    logger.exception(e)
            
            if self.args.debug and relevant_paras>self.args.debug_count:
                break

            else:
                if docs_parsed < num_docs:
                    logger.warning(f'Setting up database connection again \n')
                    self.setup_connection()
                    cursor = self.collection_input.find(self.query, no_cursor_timeout=True).skip(docs_parsed)
        
        logger.info(f'Number of total documents: {self.filtration_dict["total_docs"]}')
        logger.info(f'Number of total paragraphs: {self.filtration_dict["total_paragraphs"]}')
        logger.info(f'Number of relevant documents: {self.filtration_dict["relevant_documents"]}')
        logger.info(f'Number of documents with Tg information: {self.filtration_dict["Tg_documents"]}')
        logger.info(f'Number of documents with bandgap information: {self.filtration_dict["bandgap_documents"]}')
        logger.info(f'Number of paragraphs with Tg keywords: {self.filtration_dict["Tg_keyword_paragraphs"]}')
        logger.info(f'Number of paragraphs with bandgap keywords: {self.filtration_dict["bandgap_keyword_paragraphs"]}')
        logger.info(f'Number of paragraphs with Tg information after NER filter: {self.filtration_dict["Tg_keyword_paragraphs_ner"]}')
        logger.info(f'Number of paragraphs with bandgap information after NER filter: {self.filtration_dict["bandgap_keyword_paragraphs_ner"]}')
        logger.info(f'Number of paragraphs of conventional pipeline that resulted in errors: {self.filtration_dict["BERT_pipeline_error"]}')
        logger.info(f'Number of paragraphs with Tg information whose LLM output could not be json decoded: {self.filtration_dict["Tg_json_decode_error"]}')
        logger.info(f'Number of paragraphs with bandgap information whose LLM output could not be json decoded: {self.filtration_dict["bandgap_json_decode_error"]}')
        logger.info(f'Cost of text with Tg information: $ {(self.filtration_dict["Tg_token_count"]*self.token_cost):.2f}')
        logger.info(f'Cost of text with bandgap information: $ {(self.filtration_dict["bandgap_token_count"]*self.token_cost):.2f}')

    def process_property(self, mode, para, seed_prompt, token_count, doi, ner_output=None, output_bert={}):
        output_llm = {}
        if self.keyword_filter(keyword_list=self.metadata[mode]['coreferents'], para=para):
            self.filtration_dict[f'{mode}_keyword_paragraphs']+=1
            ner_output, ner_filter_output = self.ner_filter(para, unit_list=self.metadata[mode]['unit_list'], ner_output=ner_output)
            if ner_filter_output:
                self.filtration_dict[f'{mode}_keyword_paragraphs_ner']+=1
                # if self.args.use_llm and self.args.use_conventional_pipeline and not output_bert:
                #     tasks = [self.process_single_example_async(text=para, seed_prompt=seed_prompt, mode=mode), self.process_BERT_pipeline_async(ner_output, para, doi)]
                #     results = await asyncio.gather(*tasks)
                #     output_llm, current_token_count = results[0]
                #     output_bert = results[1]

                if self.args.use_conventional_pipeline and not output_bert:
                    output_bert = self.process_BERT_pipeline(ner_output, para, doi)
                if self.args.use_llm:
                    output_llm, current_token_count = self.process_single_example(text=para, seed_prompt=seed_prompt, mode=mode)
                    try:
                        output_dict = json.loads(output_llm)
                        output_llm = self.post_process(output_dict)
                    except Exception as e:
                        logger.info(f'Error message: {e}')
                        logger.info(f'For {doi}, output is: {output_llm}')
                        self.filtration_dict[f'{mode}_json_decode_error']+=1
                        output_llm = {}
                    self.filtration_dict[f'{mode}_token_count']+=current_token_count
                else:
                    self.filtration_dict[f'{mode}_token_count']+=self.count_tokens(self.construct_prompt(para, mode))+token_count+self.generation_constant
        
        return output_llm, output_bert, ner_output
    
    def count_tokens(self, text):
        """Count the number of tokens in the text"""
        return len(self.tokenizer(text)['input_ids'])

    def keyword_filter(self, keyword_list, para):
        """Pass a filter to only pass paragraphs with relevant information to the LLM"""
        if any([keyword in para or keyword in para.lower() for keyword in keyword_list]):
            return True
        
        return False

    def seed_construction(self, mode):
        ground_truth_data_file = self.metadata[mode]['ground_truth_data']
        with open(ground_truth_data_file, 'r') as f:
            ground_truth_data = json.load(f)
        
        data_dict = {}
        for doi, item_list in ground_truth_data.items():
            if doi in self.metadata[mode]['DOI_list']:
                data_dict[doi] = item_list[0]['abstract']
        
        message = self.construct_few_shot_prompt(data_dict, ground_truth_data, mode)
        token_count = 0

        for item in message:
            token_count+=self.count_tokens(item['content'])
        
        return message, token_count
    
    def ner_filter(self, para, unit_list, ner_output=None):
        """Pass paragraph through NER pipeline to check whether it contains relevant information"""
        if ner_output is None:
            ner_output = self.ner_pipeline(para)
        mat_flag = False
        prop_name_flag = False
        prop_value_flag = False
        for entity in ner_output:
            if entity['entity_group'] in self.material_entity_types:
                mat_flag = True
            elif entity['entity_group'] == 'PROP_NAME':
                prop_name_flag = True
            elif entity['entity_group'] == 'PROP_VALUE' and any([entity['word'].endswith(unit.lower()) for unit in unit_list]): # Using ends with to avoid false positives such as K in kPa or °C/min
                prop_value_flag = True
            
        output_flag = mat_flag and prop_name_flag and prop_value_flag
        
        return ner_output, output_flag

    def process_BERT_pipeline(self, ner_output, para, doi):
        """Process the paragraph using the BERT-based pipeline"""
        try:
            record_extraction_input = ner_feed(ner_output, para)
            relation_extractor = record_extractor.RelationExtraction(para, record_extraction_input, self.train_data, self.test_data)
            output_para, _ = relation_extractor.process_document(token_postprocessing=True)
        except Exception as e:
            self.filtration_dict['BERT_pipeline_error']+=1
            logger.warning(f'Exception {e} occurred while processing paragraph {doi} using BERT-based pipeline')
            logger.exception(e)
            output_para = {}

        return output_para
        
    def check_para_name(self, para_name):
        if para_name and para_name.lower() in self.skip_headers:  # Can make a bit more fancy to include sub-word info
            return True
        else:
            return False
    
    def para_generator(self, document_node, para_name):
        if self.check_para_name(para_name):
            yield '', para_name
        for para in document_node:
            if type(para) == dict:
                yield from self.para_generator(para['content'], para_name=para['name'])
            elif type(para) == str:
                yield para, para_name
            else:
                raise ValueError


if __name__ == '__main__':
    # args = parser.parse_args()
    args = parse_args(sys.argv[1:])
    args = args[0]
    if args.use_debugpy:
        debugpy.listen(5678)
        debugpy.wait_for_client()
        debugpy.breakpoint()
    run_inference = FullTextExtraction(args=args)
    run_inference.run_inference()

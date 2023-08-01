"""Create dataset and run API inference on the text"""
import os
import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s [%(funcName)s at %(filename)s]',
                    datefmt='%Y-%m-%d', level=logging.DEBUG)
logger = logging.getLogger()

from prompt_extraction.dataset_creation import DatasetCreation
from prompt_extraction.parse_args import parse_args
from prompt_extraction.compute_embeddings import ComputeEmbeddings
from prompt_extraction.diversity_selection import diversity_selection
from prompt_extraction.utils import compute_metrics

import openai
import polyai.api

from typing import Dict, List
from os import path, makedirs

import random
random.seed(42)
import sys
from collections import defaultdict
import torch
import debugpy
import json
from time import sleep

import config

# Setup logging

# logger.setLevel(logging.INFO)


class RunInformationExtraction:
    def __init__(self, args):
        # Setup API connection
        self.args = args
        assert args.mode in ['Tg', 'bandgap']
        self.output_path = f'{self.args.out_dir}/output/{self.args.mode}'
        
    def run_inference(self):
        """Run inference on the dataset"""
        
        self.experiment_path = path.join(self.output_path, self.args.experiment_name)
        makedirs(self.experiment_path, exist_ok=True)

        # Load dataset
        if path.exists(path.join(self.output_path, 'dataset_ground.json')) and path.exists(path.join(self.output_path, 'dataset_nlp.json')) and \
            path.exists(path.join(self.output_path, 'dataset_ground_embeddings.pt')) and not self.args.create_dataset:
            logger.info('Loading datasets from file')
            dataset_ground = json.load(open(path.join(self.output_path, 'dataset_ground.json')))
            dataset_nlp = json.load(open(path.join(self.output_path, 'dataset_nlp.json')))
        else:
            logger.debug("Creating ground and NLP json dataset.")
            dataset_ground, dataset_nlp = DatasetCreation().create_dataset(self.args.mode)
            with open(path.join(self.output_path, 'dataset_ground.json'), 'w') as f:
                json.dump(dataset_ground, f, indent=2)
            
            with open(path.join(self.output_path, 'dataset_nlp.json'), 'w') as f:
                json.dump(dataset_nlp, f, indent=2)
        
        if path.exists(path.join(self.output_path, 'dataset_ground_embeddings.pt')) and not self.args.create_embeddings:
            logger.info('Loading embeddings from file')
            dataset_ground_embeddings = torch.load(path.join(self.output_path, 'dataset_ground_embeddings.pt'))
        else:
            logger.debug("Creating embeddings file.")
            dataset_ground_embeddings = ComputeEmbeddings().run(dataset_ground, self.args.mode)
            torch.save(dataset_ground_embeddings, path.join(self.output_path, 'dataset_ground_embeddings.pt'))
        
        llm_error_doi_list = None
        if self.args.doi_error_list_file is not None:
            if path.exists(self.args.doi_error_list_file):
                with open(self.args.doi_error_list_file, 'r') as fi:
                   llm_error_doi_list = json.load(fi)
            else:
                logger.warning(f'DOI list file {self.args.doi_error_list_file} does not exist.')

        if self.args.debug:
            dataset_ground = {k: v for k, v in dataset_ground.items() if k in list(dataset_ground.keys())[:self.args.debug_count]}
            dataset_nlp = {k: v for k, v in dataset_nlp.items() if k in dataset_ground}
            logger.info(f'Running in debug mode with {self.args.debug_count} positive and {self.args.debug_count} negative DOI\'s')

        logger.info(f'Number of positive DOI\'s: {len(dataset_ground)}')
        logger.debug("Log level: DEBUG")

        dataset_llm = defaultdict(list)
        if self.args.seed_count>0:
            logger.info("Creating seed messages using the embeddings.")
            seed_message, doi_list = self.seed_prompt(dataset=dataset_ground,
                                                      dataset_embeddings=dataset_ground_embeddings,
                                                      error_doi_list=llm_error_doi_list)
            logger.info(f'Seed DOI list: {doi_list}')
        else:
            logger.info("Not using seed message.")
            seed_message = []
            doi_list = []

        total_usage = []
        json_decode_error_count = 0

        if path.exists(path.join(self.experiment_path, 'dataset_llm.json')):
            logger.info("Loading existing LLM dataset json")
            dataset_llm = json.load(open(path.join(self.experiment_path, 'dataset_llm.json')))

        else:
            logger.info("Creating LLM dataset json")
            for index, doi in enumerate(dataset_ground.keys()):
                if index%100==0:
                    logger.info(f'Done with {index} documents')
                if doi not in doi_list:
                    text = dataset_ground[doi][0]['abstract']
                    output, usage = self.process_single_example(text=text, seed_prompt=seed_message, mode=self.args.mode)
                    total_usage.append(usage)
                    try:
                        output_dict = json.loads(output)
                        current_output = self.post_process(output_dict)
                        dataset_llm[doi].extend(current_output)
                    except Exception as e:
                        logger.info(f'Error message: {e}')
                        logger.info(f'For {doi}, output is: {output}')
                        json_decode_error_count+=1

            with open(path.join(self.experiment_path, 'dataset_llm.json'), 'w') as f:
                json.dump(dataset_llm, f, indent=2)
        
            logger.info(f'Total token usage so far with positive examples: {sum(total_usage)}')
            logger.info(f'Number of JSON decode errors: {json_decode_error_count} out of {len(dataset_ground)}')

        # Compute metrics over ground truth and the LLM extracted data
        logger.info('Computing metrics over ground truth and the LLM extracted data')
        precision, recall, f1, llm_error_doi_list = compute_metrics(ground_truth=dataset_ground, extracted=dataset_llm)

        with open(path.join(self.experiment_path, 'llm_error_doi_list.json'), 'w') as f:
            json.dump(llm_error_doi_list, f, indent=2)

        llm_metrics = {
            "model": 'polyai' if self.args.polyai else 'openai',
            'precision': precision,
            'recall': recall, 'F1': f1, 'token_usage': sum(total_usage)
        }

        # Save precision, recall and f1 scores in a text file
        with open(path.join(self.experiment_path, 'metrics.txt'), 'w+') as f:
            f.write('\n')
            f.write('Metrics for LLM extracted data\n')
            f.write(f'Precision: {precision}\n')
            f.write(f'Recall: {recall}\n')
            f.write(f'F1: {f1}\n')

        # Compute metrics over ground truth and the classical NLP extracted data
        logger.info('Computing metrics over ground truth and the classical NLP extracted data')
        precision, recall, f1, _ = compute_metrics(ground_truth=dataset_ground, extracted=dataset_nlp)

        nlp_metrics = {
            "model": 'materials-bert', 'precision': precision,
            'recall': recall, 'F1': f1, 'token_usage': 0
        }

        with open(path.join(self.experiment_path, 'metrics.txt'), 'a') as f:
            f.write('\n')
            f.write('Metrics for NLP extracted data\n')
            f.write(f'Precision: {precision}\n')
            f.write(f'Recall: {recall}\n')
            f.write(f'F1: {f1}\n')
            f.write(f'Total number of tokens used: {sum(total_usage)}\n')

        with open(path.join(self.experiment_path, 'metrics.json'), 'w+') as fp:
            json.dump({'llm': llm_metrics, 'nlp': nlp_metrics}, fp, indent=2)

        # Save all the datasets created in order to examine it later
    
    def process_single_example(self, text: str, seed_prompt: List, mode: str) -> str:
        logger.debug("Constructing prompt for mode.")
        prompt = self.construct_prompt(text, mode)
        logger.debug(prompt)

        logger.debug("Performing API inference with the prompt and seed prompt.")
        output = self.api_inference(prompt, seed_prompt)

        logger.debug("Parsing prompt output.")
        output_extracted, usage = self.parse_output(output)
        # Parse the output and create parallel output
        return output_extracted, usage
    
    def min_examples(self, dataset, min_data_points=1):
        """Find the minimum length prompts for the dataset that have at least 3 data points"""
        new_data_dict = dict()
        for doi, item_list in dataset.items():
            if len(item_list)>=min_data_points and doi not in new_data_dict:
                new_data_dict[doi] = item_list[0]['abstract']
        if self.args.seed_sampling=="minimum":
            sorted_new_data_dict = dict(sorted(new_data_dict.items(), key=lambda x: len(x[1]))[:self.args.seed_count]) # can optimize further to get only k min and not sort everything
        elif self.args.seed_sampling=="random":
            sorted_new_data_dict = dict(random.sample(new_data_dict.items(), self.args.seed_count))

        return sorted_new_data_dict

    def baseline_diversity(self, ground_truth_dataset, dataset_embeddings):
        """Compute the baseline diversity of the dataset"""
        doi_list = diversity_selection(dataset_embeddings, self.args.seed_count)
        logger.info(f'Baseline diversity DOI list: {doi_list}')
        data_dict = dict()
        for doi in doi_list:
            data_dict[doi] = ground_truth_dataset[doi][0]['abstract']
        return data_dict
    
    def seed_prompt(self, dataset, dataset_embeddings, error_doi_list=None):
        """Find the minimum length prompts for the dataset and construct a message for the API. Return the message and the DOI list containing the seed documents"""
        if self.args.seed_sampling=="error_diversity":
            assert error_doi_list is not None
        
        if self.args.seed_sampling in ["minimum", "random"]:
            data_dict = self.min_examples(dataset)
            
        elif self.args.seed_sampling=="error_diversity" and error_doi_list is not None:
            filtered_dataset_embeddings = {key: value for key, value in dataset_embeddings.items() if key in error_doi_list}
            data_dict = self.baseline_diversity(dataset, filtered_dataset_embeddings)
        
        elif self.args.seed_sampling=="baseline_diversity":
            data_dict = self.baseline_diversity(dataset, dataset_embeddings)
        else:
            raise ValueError(f'Invalid seed sampling method: {self.args.seed_sampling}')

        doi_list = list(data_dict.keys())
        message = self.construct_few_shot_prompt(data_dict, dataset, self.args.mode)
        return message, doi_list

    def construct_few_shot_prompt(self, input_dataset: Dict[str, str], dataset_ground, mode: str):
        # message = [{"role": "system", "content": "You parse structured information from unstructured text"}]
        message = []
        for doi, text in input_dataset.items():
            prompt = self.construct_prompt(text, mode)
            message.append({"role": "user", "content": prompt})
            ground_truth_list = dataset_ground[doi]
            data_dict = dict()
            for item in ground_truth_list:
                data_dict[item['material']] = item['property_value']

            message.append({"role": "assistant", "content": json.dumps(data_dict)})
        
        return message

    def construct_prompt(self, text, mode):
        """Construct the prompt for the API"""
        if mode == "Tg":
            prompt_dict = {0: 'Extract all glass transition temperature values from the following text in json format with units: ',
                                1: 'Extract all Tg values from the following text in json format with units: ', 
                                2: 'Extract all Tg values from the following text in json format: ',
                                3: 'Extract all glass transition temperature values from the following text: ',
                                4: 'Extract all glass transition temperature values: ',
                                5: 'Extract all glass transition temperature values from the text after : in json format with units. Use material name as key and property value with unit as the corresponding value like {"PE": "100 ° C"}. Do not extract any other properties: '
                                }
        elif mode == "bandgap":
            prompt_dict = {0: 'Extract all bandgap values from the following text in json format with units: ',
                                1: 'Extract all Eg values from the following text in json format with units: ', 
                                2: 'Extract all Eg values from the following text in json format: ',
                                3: 'Extract all bandgap values from the following text: ',
                                4: 'Extract all bandgap values: ',
                                5: 'Extract all bandgap values from the text after : in json format with units. Use material name as key and property value with unit as the corresponding value like {"PE": "2.3 eV"}. Do not extract any other properties: '
                                }
        prompt = prompt_dict[self.args.prompt_index] + text # Assume a fixed prompt index, may also cycle through prompts
        return prompt
    
    def api_inference(self, prompt, seed_message):
        """Run inference on the API"""
        max_retries = 5
        exponential_base = 2
        jitter = 0.1
        delay = 2
        num_retries = 0
        seed_message.append({"role": "user", "content": prompt})
        while True:
            try:
                if self.args.polyai:
                    output = polyai.api.ChatCompletion.create(
                                                model="polyai",
                                                messages=seed_message,
                                                temperature=0.01)
                else:
                    output = openai.ChatCompletion.create(
                                                model="gpt-3.5-turbo",
                                                messages=seed_message,
                                                temperature=0.01)
                break

            # Retry on specified errors
            except Exception as e:
                # Increment retries
                num_retries += 1

                # Check if max retries has been reached
                if num_retries > max_retries:
                    seed_message.pop()
                    if self.args.polyai:
                        sleep(60)
                    else:
                        raise Exception(
                            f"Maximum number of retries ({max_retries}) exceeded."
                        )

                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())

                # Sleep for the delay
                sleep(delay)

            # Raise exceptions for any errors not specified
            # except Exception as e:
            #     raise e
       
        seed_message.pop()
        sleep(0.5)
        return output

    def post_process(self, input_dict):
        """Post process the output from the API"""
        output_list = []
        for material, value in input_dict.items():
            output_list.append({'material': material, 'property_value': value})
        
        return output_list
        
    def parse_output(self, output):
        """Parse the output from the API"""
        str_output = output["choices"][0]["message"]["content"]
        usage = output["usage"]["total_tokens"]
        logger.debug(f"Total {usage} tokens: {str_output}")
        return str_output, usage


if __name__ == '__main__':
    import dotenv
    if not dotenv.load_dotenv():
        logger.warning("WARN!! .env not loaded")

    openai.api_key = os.getenv('OPENAI_API_KEY')

    # args = parser.parse_args()
    args = parse_args(sys.argv[1:])
    args = args[0]
    if args.use_debugpy:
        debugpy.listen(5678)
        debugpy.wait_for_client()
        debugpy.breakpoint()

    if args.polyai:
        polyai.api.api_key = os.environ.get("POLYAI_API_KEY")

    if not openai.api_key and not polyai.api.api_key:
        logger.error("API key not loaded")

    config.DATA_DIR = args.out_dir
    run_inference = RunInformationExtraction(args=args)
    run_inference.run_inference()

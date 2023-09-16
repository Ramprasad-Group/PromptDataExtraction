import os
import sys
import pylogg as log

from collections import defaultdict

from backend import postgres, sett
from backend.postgres.orm import Papers, FilteredPapers, PaperTexts, FilteredParagraphs, PropertyMetadata
from backend.utils import checkpoint

import pranav.prompt_extraction.config
from pranav.prompt_extraction.run_inference import RunInformationExtraction
from pranav.prompt_extraction.parse_args import parse_args
from pranav.prompt_extraction.utils import connect_remote_database, LoadNormalizationDataset, ner_feed
from pranav.prompt_extraction.pre_processing import PreProcessor
# from pranav.prompt_extraction.run_inference import RunInformationExtraction

import json
import torch    

from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC']

filtration_dict = defaultdict(int)

# Load NER model
if torch.cuda.is_available():
	log.info('GPU device found')
	device = 0
else:
	device = 'cpu'

normalization_dataloader = LoadNormalizationDataset()
# train_data, test_data = normalization_dataloader.process_normalization_files()

# Load model and tokenizer
model_file = 'backend/models/MaterialsBERT'
tokenizer = AutoTokenizer.from_pretrained(model_file, model_max_length=512)
model = AutoModelForTokenClassification.from_pretrained(model_file)
ner_pipeline = pipeline(task="ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple", device=device)

pre_processor = PreProcessor()

token_cost = 0.002/1000 # Cost per token in dollars
generation_constant = 30


def add_to_filtered_paragrahs(para_id, ner_filter_name):
	paragraph = FilteredParagraphs().get_one(db, {'para_id': para_id, 'filter_name': ner_filter_name})
	if paragraph is not None:
		log.trace(f"Paragraph in PostGres: {para_id}. Skipped.")
		return False
	
	else:
		obj = FilteredParagraphs()
		obj.para_id = para_id
		obj.filter_name = ner_filter_name
		obj.insert(db)

		log.trace(f"Added to PostGres: {para_id}")


def ner_filter_check(property: str, publisher_directory: str, prop_filter_name: str, ner_filter_name:str):
	mode = property.replace(" ", "_")

	prop_metadata = PropertyMetadata().get_one(db, {"name": property})
	
	#selecting paragraphs that have passed the heuristic filter check for property
	paragraphs = (db.query(FilteredParagraphs.para_id, PaperTexts.text)
							 .join(PaperTexts, FilteredParagraphs.para_id == PaperTexts.id)
							 .filter(FilteredParagraphs.filter_name == prop_filter_name)
							 .order_by(PaperTexts.id)
							 .all())

	last_processed_id = checkpoint.get_last(db, name= ner_filter_name, table= PaperTexts.__tablename__)

	relevant_paras = 0
	#para_id has corresponding id and text
	for para in paragraphs:

		para_id = para[0]
		para_text = para[1]

		if para_id <= last_processed_id:
			continue

		if sett.Run.debugCount >0:
			if filtration_dict['total_paragraphs'] > sett.Run.debugCount:
				break

		filtration_dict['total_paragraphs'] +=1

		ner_output, ner_filter_output = ner_filter(para_text, unit_list= prop_metadata.units, ner_output=None)
		if ner_filter_output:
			log.note(f'Paragraph: {para_id} passed {ner_filter_name}.')
			filtration_dict[f'{mode}_keyword_paragraphs_ner']+=1
			if add_to_filtered_paragrahs(para_id, ner_filter_name):
				relevant_paras +=1

				if relevant_paras % 50 == 0:
					db.commit()

		else:
			log.info(f"{para_id} did not pass {ner_filter_name}")

		if filtration_dict['total_paragraphs']% 100 == 0 or filtration_dict['total_paragraphs']== len(paragraphs):
			log.info(f'Number of total paragraphs: {filtration_dict["total_paragraphs"]}')
			log.info(f'Number of paragraphs with {property} information after heuristic filter: {len(paragraphs)}')
			log.info(f'Number of paragraphs with {property} information after NER filter ({ner_filter_name}) : {filtration_dict[f"{mode}_keyword_paragraphs_ner"]}')


	checkpoint.add_new(db, name = ner_filter_name, table = PaperTexts.__tablename__, row = para_id, 
										comment = {'publisher': publisher_directory, 'filter': ner_filter_name, 
										'debug': True if sett.Run.debugCount > 0 else False, 'user': 'sonakshi'})
	log.note(f'Last processed para_id: {para_id}')
	db.commit()



def ner_filter(para_text, unit_list, ner_output=None):
	"""Pass paragraph through NER pipeline to check whether it contains relevant information"""
	if ner_output is None:
			ner_output = ner_pipeline(para_text)
	mat_flag = False
	prop_name_flag = False
	prop_value_flag = False
	for entity in ner_output:
			if entity['entity_group'] in material_entity_types:
					mat_flag = True
			elif entity['entity_group'] == 'PROP_NAME':
					prop_name_flag = True
			elif entity['entity_group'] == 'PROP_VALUE' and any([entity['word'].endswith(unit.lower()) for unit in unit_list]): # Using ends with to avoid false positives such as K in kPa or °C/min
					prop_value_flag = True
			
	output_flag = mat_flag and prop_name_flag and prop_value_flag
	
	return ner_output, output_flag


def log_run_info(property, publisher_directory):
		"""
				Log run information for reference purposes.
				Returns a log Timer.
		"""
		t1 = log.note(f"NER Filter Run for property: {property} and publisher: {publisher_directory}")
		log.info("CWD: {}", os.getcwd())
		log.info("Host: {}", os.uname())

		if sett.Run.debugCount > 0:
				log.note("Debug run. Will parse maximum {} files.",
								 sett.Run.debugCount)
		else:
				log.note("Production run. Will parse all files.")

		log.info("Using loglevel = {}", sett.Run.logLevel)

		return t1


if __name__ == '__main__':
	
	publisher_directory = 'acs'
	property = "melting temperature"
	filename = property.replace(" ", "_")
	prop_filter_name = 'property_tm'
	ner_filter_name = 'ner_tm'
	
	#set the reqd directory in settings.yaml
	os.makedirs(sett.Run.directory, exist_ok=True)
	log.setFile(open(sett.Run.directory+f"/ner_{publisher_directory}_{filename}.log", "w+"))
	log.setLevel(sett.Run.logLevel)
	log.setFileTimes(show=True)
	log.setConsoleTimes(show=True)
		
	t1 = log_run_info(property, publisher_directory)
	
	ner_filter_check(property= property, publisher_directory= publisher_directory, 
									prop_filter_name=prop_filter_name, ner_filter_name= ner_filter_name)
		
	t1.done("All Done.")

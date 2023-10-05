import os
import sys
import pylogg as log
from tqdm import tqdm

from collections import defaultdict

from backend import postgres, sett
from backend.postgres.orm import Papers, FilteredPapers, PaperTexts, FilteredParagraphs, PropertyMetadata
from backend.utils import checkpoint
from backend.console.heuristic_filter import FilterPropertyName

import torch    

from backend.record_extraction import bert_model

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


# Load Materials bert to GPU
bert = bert_model.MaterialsBERT()
bert.init_local_model(
	sett.NERPipeline.model, sett.NERPipeline.pytorch_device)
ner_pipeline = bert.pipeline


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
	# paragraphs = (db.query(FilteredParagraphs.para_id, PaperTexts.text)
	# 						 .join(PaperTexts, FilteredParagraphs.para_id == PaperTexts.id)
	# 						 .filter(FilteredParagraphs.filter_name == prop_filter_name)
	# 						 .order_by(PaperTexts.id)
	# 						 .all())
	
	last_processed_id = checkpoint.get_last(db, name= ner_filter_name, table= FilteredParagraphs.__tablename__)
	log.info("Last run row ID: {}", last_processed_id)

	query = '''
	SELECT fp.para_id, pt.text
	FROM filtered_paragraphs fp
	JOIN paper_texts pt ON fp.para_id = pt.id
	WHERE fp.filter_name = :prop_filter_name
	AND fp.para_id > :last_processed_id ORDER BY fp.para_id LIMIT :limit;
	'''

	log.info("Querying list of non-processed paragraphs.")
	records = postgres.raw_sql(query, {'prop_filter_name': prop_filter_name, 'last_processed_id': last_processed_id, 'limit': 10000000})
	log.note("Found {} paragraphs not processed.", len(records))

	if len(records) == 0:
		return
	else:
		log.note("Unprocessed Row IDs: {} to {}",
							records[0].para_id, records[-1].para_id)

	relevant_paras = 0
	#para_id has corresponding id and text
	# for para in paragraphs:

	for row in tqdm(records):

		if row.para_id < last_processed_id:
			continue

		# para_id = para[0]
		# para_text = para[1]
		# if para_id <= last_processed_id:
		# 	continue

		if sett.Run.debugCount >0 and filtration_dict['total_paragraphs'] > sett.Run.debugCount:
				break

		filtration_dict['total_paragraphs'] +=1

		para = PaperTexts().get_one(db, {'id': row.para_id})

		ner_output, ner_filter_output = ner_filter(para_text=para.text, unit_list= prop_metadata.units, ner_output=None)
		if ner_filter_output:
			log.note(f'Paragraph: {row.para_id} passed {ner_filter_name}.')
			filtration_dict[f'{mode}_keyword_paragraphs_ner']+=1
			if add_to_filtered_paragrahs(row.para_id, ner_filter_name):
				relevant_paras +=1

				if relevant_paras % 50 == 0:
					db.commit()

		else:
			log.info(f"{row.para_id} did not pass {ner_filter_name}")

		if filtration_dict['total_paragraphs']% 100 == 0 or filtration_dict['total_paragraphs']== len(records):
			log.info(f'Number of total paragraphs: {filtration_dict["total_paragraphs"]}')
			log.info(f'Number of paragraphs with {property} information after heuristic filter: {len(records)}')
			log.info(f'Number of paragraphs with {property} information after NER filter ({ner_filter_name}) : {filtration_dict[f"{mode}_keyword_paragraphs_ner"]}')


	checkpoint.add_new(db, name = ner_filter_name, table = FilteredParagraphs.__tablename__, row = row.para_id, 
										comment = {'user': 'sonakshi', 'filter': ner_filter_name, 
										'debug': True if sett.Run.debugCount > 0 else False })
	log.note(f'Last processed para_id: {row.para_id}')
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


def log_run_info(property, publisher_directory, ner_filter_name):
		"""
				Log run information for reference purposes.
				Returns a log Timer.
		"""
		t1 = log.note(f"NER Filter Run ({ner_filter_name}) for property: {property} and publisher: {publisher_directory}")
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
	
	publisher_directory = 'all'
	prop_filter_name = 'ionic_cond-hf-sel1k'
	ner_filter_name = 'ionic_cond-ner-sel1k'

	property = "ionic conductivity"
	# property = getattr(FilterPropertyName, prop_filter_name)
	filename = property.replace(" ", "_")
	
	#set the reqd directory in settings.yaml
	os.makedirs(sett.Run.directory, exist_ok=True)
	log.setFile(open(sett.Run.directory+f"/ner_{ner_filter_name}.log", "w+"))
	log.setLevel(sett.Run.logLevel)
	log.setFileTimes(show=True)
	log.setConsoleTimes(show=True)
		
	t1 = log_run_info(property, publisher_directory, ner_filter_name)
	
	ner_filter_check(property= property, publisher_directory= publisher_directory, 
									prop_filter_name=prop_filter_name, ner_filter_name= ner_filter_name)
		
	t1.done("All Done.")

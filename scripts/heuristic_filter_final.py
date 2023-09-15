import os
import sys
import pylogg as log

from collections import defaultdict

from backend import postgres, sett
from backend.postgres.orm import Papers, FilteredPapers, PaperTexts, FilteredParagraphs, PropertyMetadata

# import pranav.prompt_extraction.config
# from pranav.prompt_extraction.run_inference import RunInformationExtraction
# from pranav.prompt_extraction.parse_args import parse_args
# from pranav.prompt_extraction.utils import connect_remote_database, LoadNormalizationDataset, ner_feed
# from pranav.prompt_extraction.pre_processing import PreProcessor
# from pranav.prompt_extraction.run_inference import RunInformationExtraction

import json
import torch    

from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

# class HeuristicFilter(RunInformationExtraction):
# 	def __init__(self, args):
# 		super(HeuristicFilter, self).__init__(args=args)

metadata = {'Tg':{'ground_truth_data': f'data/glass_transition_temperature/dataset_ground.json',
												'coreferents': ['Tg', 'T_{g}', 'T g', 'T_{g})', "T_{g} 's", 'glass transition', 'glass transitions', 'glass transition temperature', 'glass transition temperatures', 'glass transition temperatures', 'T_{g}s', 'glass-transition temperatures'],
												'DOI_list': ['10.1002/pola.1179', '10.1002/app.34170'],
												'unit_list': ['K', '° C', '°C']
												},
								'bandgap':{'ground_truth_data': f'data/bandgap/dataset_ground.json',
												'coreferents': ['bandgap', 'band gap', 'band-gap', 'band-gaps', 'bandgaps', 'band gaps', 'E_{g}', 'optical bandgap', 'optical band gap', 'optical band gaps', 'optical bandgaps', 'bandgap energies', 'optical energy bandgaps', 'optical energy gap', 'energy bandgap', 'optical band-gaps', 'optical-band-gap energies', 'optical band-gap', 'optical band gap energy', 'band gap energies', 'band gap energy', 'electrochemical band gap', 'electrochemical band gaps', 'Eg'],
												'DOI_list': ['10.1039/c8nj04453h', '10.1021/cm202247a', '10.1016/j.eurpolymj.2014.07.006'],
												'unit_list': ['eV']
												}
								}
material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC']

filtration_dict = defaultdict(int)



def add_to_filtered_paragrahs(para, filter_name, found_status):
	paragraph = FilteredParagraphs().get_one(db, {'para_id': para.id})
	setattr(filter_name)

	#if paragraph found update the entry corresponding to filter_name
	if paragraph is not None:
		paragraph.filter_name = found_status
		# db.commit()
		log.trace(f"Paragraph in PostGres: {para.id}. Updated {filter_name} status.")

	else:
		#if paragraph not found in table, add entry
		obj = FilteredParagraphs()
		obj.para_id = para.id
		obj.filter_name = found_status
		obj.insert(db)
		log.trace(f"Added paragraph to PostGres: {para.id}")

	if found_status:
		log.note(f"{para.id} passed the heuristic filter.")
	else:
		log.trace(f"{para.id} did not pass the heuristic filter.")

			

	
def heuristic_filter(property:str, publisher_directory:str, filter_name:str):
	mode = property.replace(" ", "_")
	filter_name = filter_name

	prop_metadata = PropertyMetadata().get_one(db, {"name": property})
	keyword_list = prop_metadata.other_names

	#extract all paragraphs from polymer DOIs belonging to a particular publisher 
	poly_entries =  (db.query(FilteredPapers)
							.join(Papers, FilteredPapers.doi == Papers.doi)
							.filter(Papers.directory == publisher_directory)
							.order_by(FilteredPapers.id)
							.all())

	poly_dois = [entry.doi for entry in poly_entries]

	log.info(f'Number of documents belonging to publisher {publisher_directory}: {len(poly_dois)}')

	parsed_para = 0
	processed_dois = 0
	
	for doi in poly_dois:
		if sett.Run.debugCount >0:
			if filtration_dict['total_dois'] > sett.Run.debugCount:
				break
			
		log.trace(f"Processing {doi}")

		filtration_dict['total_dois'] +=1

		paragraphs = PaperTexts().get_all(db, {'doi': doi})
		log.trace(f'Number of paragraphs found: {len(paragraphs)}')
		
		# relevant_doi = False
		relevant_doi_paras = 0

		for para in paragraphs:
			filtration_dict['total_paragraphs'] +=1
			found = process_property(mode= mode,keyword_list=keyword_list, para= para, prop_metadata=prop_metadata)
			add_to_filtered_paragrahs(para=para, filter_name = filter_name, found_status= found)
			
			if filtration_dict['total_paragraphs'] % 1 == 0:
				db.commit()
			
			if found:
				relevant_doi_paras +=1

		if relevant_doi_paras>0:
			filtration_dict[f"{mode}_documents"] +=1
			log.note(f'DOI: {doi} contains paragraphs for property: {mode}.')


		if filtration_dict['total_dois']% 100 == 0 or filtration_dict['total_dois']== sett.Run.debugCount:
			log.info(f'Number of total documents: {filtration_dict["total_dois"]}')
			log.info(f'Number of total paragraphs: {filtration_dict["total_paragraphs"]}')
			# log.note(f'Number of relevant documents: {filtration_dict["relevant_documents"]}')
			log.info(f'Number of documents with {property} information: {filtration_dict[f"{mode}_documents"]}')
			log.info(f'Number of paragraphs with {property} keywords: {filtration_dict[f"{mode}_keyword_paragraphs"]}')
			log.info(f'Number of paragraphs with {property} information after NER filter: {filtration_dict[f"{mode}_keyword_paragraphs_ner"]}')
			log.info(f'Last processed para_id: {para.id}')


def keyword_filter(keyword_list, para):
	"""Pass a filter to only pass paragraphs with relevant information to the LLM"""
	if any([keyword in para.text or keyword in para.text.lower() for keyword in keyword_list]):
		return True
	
	return False

def process_property(mode, keyword_list, para, prop_metadata, ner_filter= False):
	if keyword_filter(keyword_list, para):
		filtration_dict[f'{mode}_keyword_paragraphs']+=1
		return True
	return False


def log_run_info(property, publisher_directory):
		"""
				Log run information for reference purposes.
				Returns a log Timer.
		"""
		t1 = log.note(f"Heuristic Filter Run for property: {property} and publisher: {publisher_directory}")
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
	
	publisher_directory = 'rsc'
	property = "thermal decomposition temperature"
	filename = property.replace(" ", "_")
	filter_name = 'property_td'
	
	os.makedirs(sett.Run.directory, exist_ok=True)
	log.setFile(open(sett.Run.directory+f"/hf_{publisher_directory}_{filename}.log", "w+"))
	log.setLevel(sett.Run.logLevel)
	log.setFileTimes(show=True)
	log.setConsoleTimes(show=True)
		
	t1 = log_run_info(property, publisher_directory)
	
	heuristic_filter(property= property, publisher_directory= publisher_directory, filter_name=filter_name)
		
	t1.done("All Done.")
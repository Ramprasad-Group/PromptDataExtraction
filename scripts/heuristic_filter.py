import os
import sys
import pylogg as log
from tqdm import tqdm

from collections import defaultdict

from backend import postgres, sett
from backend.postgres.orm import Papers, FilteredPapers, PaperTexts, FilteredParagraphs, PropertyMetadata
from backend.utils import checkpoint


sett.load_settings()
postgres.load_settings()
db = postgres.connect()


material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC']

filtration_dict = defaultdict(int)



def add_to_filtered_paragrahs(para_id, filter_name):
	paragraph = FilteredParagraphs().get_one(db, {'para_id': para_id, 'filter_name': filter_name})
	if paragraph is not None:
		log.trace(f"Paragraph in PostGres: {para_id}. Skipped.")
		return False
	
	else:
		obj = FilteredParagraphs()
		obj.para_id = para_id
		obj.filter_name = filter_name
		obj.insert(db)

		log.trace(f"Added to PostGres: {para_id}")

		return True
			

def heuristic_filter_check(property:str, publisher_directory:str, filter_name:str):
	mode = property.replace(" ", "_")
	filter_name = filter_name

	prop_metadata = PropertyMetadata().get_one(db, {"name": property})
	keyword_list = prop_metadata.other_names

	last_processed_id = checkpoint.get_last(db, name= filter_name, table= PaperTexts.__tablename__)
	log.info("Last run row ID: {}", last_processed_id)

	query= '''
	SELECT pt.id AS para_id FROM paper_texts pt
	JOIN filtered_papers fp ON fp.doi = pt.doi
	WHERE pt.id > :last_processed_id ORDER BY pt.id LIMIT :limit;
	'''

	log.info("Querying list of non-processed paragraphs.")
	records = postgres.raw_sql(query, {'last_processed_id': last_processed_id, 'limit': 10000000})
	log.note("Found {} paragraphs not processed.", len(records))

	if len(records) == 0:
		return
	else:
		log.note("Unprocessed Row IDs: {} to {}",
							records[0].para_id, records[-1].para_id)
	
	relevant_paras = 0
	
	for row in tqdm(records):
		if row.para_id < last_processed_id:
			continue

		if sett.Run.debugCount >0 and filtration_dict['total_paragraphs'] > sett.Run.debugCount:
			break

		filtration_dict['total_paragraphs'] +=1

		# Fetch the paragraph texts.
		para = PaperTexts().get_one(db, {'id': row.para_id})

		found = process_property(mode= mode,keyword_list=keyword_list, para= para, 
														prop_metadata=prop_metadata, ner_filter=False, heuristic_filter=True)
			
		if found:
			log.note(f"{para.id} passed the heuristic filter ")
			relevant_paras +=1

			if add_to_filtered_paragrahs(para_id= row.para_id, filter_name = filter_name):
				if relevant_paras % 20 == 0:
					db.commit()
				

		else:
			log.info(f"{para.id} did not pass the heuristic filter")
			# log.trace(para.text)

		if filtration_dict['total_paragraphs']% 100 == 0 or filtration_dict['total_paragraphs']== len(records):
			log.info(f'Number of total paragraphs: {filtration_dict["total_paragraphs"]}')
			# log.info(f'Number of documents with {property} information: {filtration_dict[f"{mode}_documents"]}')
			log.info(f'Number of paragraphs with {property} keywords: {filtration_dict[f"{mode}_keyword_paragraphs"]}')
	
	log.info(f'Last processed para_id: {row.para_id}')

	checkpoint.add_new(db, name = filter_name, table = PaperTexts.__tablename__, row = row.para_id, 
										comment = {'user': 'sonakshi', 'filter': filter_name,
										'debug': True if sett.Run.debugCount > 0 else False})
	
	db.commit()


def keyword_filter(keyword_list, para):
	"""Pass a filter to only pass paragraphs with relevant information to the LLM"""
	if any([keyword in para.text or keyword in para.text.lower() for keyword in keyword_list]):
		return True
	
	return False

def process_property(mode, keyword_list, para, prop_metadata, ner_filter= False, heuristic_filter = True):
	if heuristic_filter:
		if keyword_filter(keyword_list, para):
			filtration_dict[f'{mode}_keyword_paragraphs']+=1
			return True


def log_run_info(property, publisher_directory, filter_name):
    """
        Log run information for reference purposes.
        Returns a log Timer.
    """
    t1 = log.note(f"Heuristic Filter ({filter_name}) Run for property: {property} and publisher: {publisher_directory}")
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
	
	publisher_directory = 'All'
	property = 'hardness'
	filter_name = 'property_hardness' 

	filename = property.replace(" ", "_")
	
	os.makedirs(sett.Run.directory, exist_ok=True)
	# log.setFile(open(sett.Run.directory+f"/hf_{publisher_directory}_{filename}.log", "w+"))
	log.setFile(open(sett.Run.directory+f"/hf_{filename}.log", "w+"))
	log.setLevel(sett.Run.logLevel)
	log.setFileTimes(show=True)
	log.setConsoleTimes(show=True)
		
	t1 = log_run_info(property, publisher_directory, filter_name)
	
	heuristic_filter_check(property= property, publisher_directory= publisher_directory, filter_name=filter_name)
		
	t1.done("All Done.")

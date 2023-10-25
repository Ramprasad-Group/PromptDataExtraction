import pylogg
from tqdm import tqdm

import argcomplete
from argparse import ArgumentParser, _SubParsersAction
from backend.postgres.orm import FilteredParagraphs, PaperTexts, PropertyMetadata

from collections import defaultdict

ScriptName = 'heuristic-filter'

log = pylogg.New(ScriptName)

# material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC']
filtration_dict = defaultdict(int)

class FilterPropertyName:
	property_tg = 'glass transition temperature'
	property_tm = 'melting temperature'
	property_td = 'thermal decomposition temperature'
	property_thermal_conductivity = 'thermal conductivity'
	property_bandgap = 'bandgap'
	property_ts = 'tensile strength'
	property_ym = 'youngs modulus'
	property_eab = 'elongation at break'
	property_cs = 'compressive strength'
	property_is = 'impact strength'
	property_hardness = 'hardness'
	property_fs = 'flexural strength'
	property_ionic_cond = 'ionic conductivity'
	property_wca = 'water contact angle'
	property_dc= 'dielectric constant'
	property_density = 'density'
	property_loi = 'limiting oxygen index'
	property_iec = 'ion exchange capacity'
	property_lcst = 'lower critical solution temperature'
	property_ucst = 'upper critical solution temperature'
	property_co2_perm = 'CO_{2} permeability'
	property_ct = 'crystallization temperature'
	property_ri = 'refractive index'
	property_wu = 'water uptake'
	property_sd = 'swelling degree'
	property_o2_perm = 'O_{2} permeability'
	property_h2_perm = 'H_{2} permeability'
	property_methanol_perm = 'methanol permeability'
	

def add_args(subparsers: _SubParsersAction):
	parser: ArgumentParser = subparsers.add_parser(
			ScriptName,
			help= 'Run Heuristic filter pipeline on unprocessed paragraph rows.')
	parser.add_argument(
			"-r", "--filter", default='', choices=list(FilterPropertyName.__dict__.keys()), 
			help= "Name of the property filter. Should look like property_*")
	argcomplete.autocomplete(parser)

	## add property argument 
	parser.add_argument(
			"-l", "--limit", default=10000000, type=int,
			help="Number of paragraphs to process. Default: 10000000")
		

def add_to_filtered_paragrahs(db, para_id, filter_name):
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


def run(args: ArgumentParser):
	from backend import postgres, sett
	from backend.utils import checkpoint

	db = postgres.connect()
	
	runinfo = {
		'user': sett.Run.userName,
		'filter': args.filter,
		}
	
	last_processed_id = checkpoint.get_last(db, name= args.filter, table= PaperTexts.__tablename__)
	log.info("Last run row ID: {}", last_processed_id)

	# Query the unprocessed list of rows.
	query= '''
	SELECT pt.id AS para_id FROM paper_texts pt
	JOIN filtered_papers fp ON fp.doi = pt.doi
	WHERE pt.id > :last_processed_id ORDER BY pt.id LIMIT :limit;
	'''

	# #Query for sel1k
	# query = '''
	# SELECT pt.id AS para_id FROM paper_texts pt
	# JOIN filtered_papers fp ON fp.doi = pt.doi
	# WHERE pt.id > :last_processed_id
	# AND fp.filter_name = 'select-1k'
	# ORDER BY pt.id
	# LIMIT :limit;
	# '''

	t2 = log.info("Querying list of non-processed paragraphs.")
	records = postgres.raw_sql(query, {'last_processed_id': last_processed_id, 'limit': args.limit})
	t2.note("Found {} paragraphs not processed.", len(records))

	if len(records) == 0:
		return
	else:
		log.note("Unprocessed Row IDs: {} to {}",
							records[0].para_id, records[-1].para_id)
	

	property = getattr(FilterPropertyName, args.filter)
	mode = property.replace(" ", "_")

	prop_metadata = PropertyMetadata().get_one(db, {"name": property})
	keyword_list = prop_metadata.other_names
	
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

			if add_to_filtered_paragrahs(db, para_id= row.para_id, filter_name = args.filter):
				if relevant_paras % 50 == 0:
					db.commit()
				

		else:
			log.info(f"{para.id} did not pass the heuristic filter")
			# log.trace(para.text)

		if filtration_dict['total_paragraphs']% 100 == 0 or filtration_dict['total_paragraphs']== len(records):
			log.info(f'Number of total paragraphs: {filtration_dict["total_paragraphs"]}')
			log.info(f'Number of paragraphs with {property} keywords: {filtration_dict[f"{mode}_keyword_paragraphs"]}')
	
	log.info(f'Last processed para_id: {row.para_id}')

	checkpoint.add_new(db, name = args.filter, table = PaperTexts.__tablename__, row = row.para_id, 
										comment = {'user': sett.Run.userName, 'filter': args.filter,
										'debug': True if sett.Run.debugCount > 0 else False})
	
	db.commit()



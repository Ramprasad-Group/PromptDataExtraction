import pylogg
from tqdm import tqdm

import argcomplete
from argparse import ArgumentParser, _SubParsersAction
from backend.postgres.orm import FilteredParagraphs, PaperTexts, PropertyMetadata
from backend.console.heuristic_filter import FilterPropertyName

from collections import defaultdict

ScriptName = 'ps-ner-filter'

log = pylogg.New(ScriptName)

material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC', 'INORGANIC']
filtration_dict = defaultdict(int)

class HeuristicFilterName:
	tg_ner_full = 'property_tg'
	tm_ner_full = 'property_tm'
	td_ner_full = 'property_td'
	thermal_conductivity_ner_full = 'property_thermal_conductivity'
	bandgap_ner_full =  'property_bandgap'
	ts_ner_full = 'property_ts'
	ym_ner_full = 'property_ym'
	eab_ner_full = 'property_eab'
	cs_ner_full = 'property_cs'
	is_ner_full = 'property_is'
	hardness_ner_full = 'property_hardness'
	fs_ner_full = 'property_fs'
	ionic_cond_ner_full ="property_ionic_cond"
	wca_ner_full = "property_wca" 
	dc_ner_full = "property_dc" 
	density_ner_full = "property_density" 
	loi_ner_full = "property_loi" 
	iec_ner_full = "property_iec"
	lcst_ner_full = "property_lcst"
	ucst_ner_full = "property_ucst" 
	co2_perm_ner_full = "property_co2_perm" 
	ct_ner_full = "property_ct" 
	ri_ner_full = "property_ri" 
	wu_ner_full = "property_wu"
	sd_ner_full = "property_sd"
	o2_perm_ner_full = "property_o2_perm" 
	h2_perm_ner_full = "property_h2_perm"
	methanol_perm_ner_full = "property_methanol_perm"


def add_args(subparsers: _SubParsersAction):
	parser: ArgumentParser = subparsers.add_parser(
			ScriptName,
			help= 'Run property specific NER filter pipeline on unprocessed paragraph rows.')
	parser.add_argument(
			"-r", "--filter", default='', choices=list(HeuristicFilterName.__dict__.keys()), 
			help= "Name of the ner filter. Should look like ner_*")
	argcomplete.autocomplete(parser)

	## add property argument 
	parser.add_argument(
			"-l", "--limit", default=1000000, type=int,
			help="Number of paragraphs to process. Default: 1000000")
		 

def _add_to_filtered_paragrahs(db, para_id, ner_filter_name):
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


def _ner_filter(ner_pipeline, para_text, unit_list, ner_output=None):

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
			elif entity['entity_group'] == 'PROP_VALUE':
				#  and any([entity['word'].endswith(unit.lower()) for unit in unit_list]): # Using ends with to avoid false positives such as K in kPa or °C/min
					prop_value_flag = True
			
	output_flag = mat_flag and prop_name_flag and prop_value_flag
	
	return ner_output, output_flag


def run(args: ArgumentParser):
	from backend import postgres, sett
	from backend.utils import checkpoint
	from backend.record_extraction import bert_model

	db = postgres.connect()

	# Load Materials bert to GPU
	bert = bert_model.MaterialsBERT()
	bert.init_local_model(
		sett.NERPipeline.model, sett.NERPipeline.pytorch_device)
	ner_pipeline = bert.pipeline

	prop_filter_name = getattr(HeuristicFilterName, args.filter)
	ner_filter_name = args.filter
	property = getattr(FilterPropertyName, prop_filter_name)
	mode = property.replace(" ", "_")
	prop_metadata = PropertyMetadata().get_one(db, {"name": property})

	last_processed_id = checkpoint.get_last(db, name= args.filter, table= FilteredParagraphs.__tablename__)
	log.info("Last run row ID: {}", last_processed_id)

	query = '''
	SELECT fp.para_id, pt.text
	FROM filtered_paragraphs fp
	JOIN paper_texts pt ON fp.para_id = pt.id
	WHERE fp.filter_name = :prop_filter_name
	AND fp.para_id > :last_processed_id ORDER BY fp.para_id LIMIT :limit;
	'''

	log.info("Querying list of non-processed paragraphs.")
	records = postgres.raw_sql(query, {
		'prop_filter_name': prop_filter_name,
		'last_processed_id': last_processed_id, 'limit': args.limit
	})
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

		para = PaperTexts().get_one(db, {'id': row.para_id})

		ner_output, ner_filter_output = _ner_filter(ner_pipeline, para_text=para.text, unit_list= prop_metadata.units, ner_output=None)
		if ner_filter_output:
			log.note(f'Paragraph: {row.para_id} passed {ner_filter_name}.')
			filtration_dict[f'{mode}_keyword_paragraphs_ner']+=1
			if _add_to_filtered_paragrahs(db, row.para_id, ner_filter_name):
				relevant_paras +=1
				if relevant_paras % 50 == 0:
					db.commit()

		else:
			log.info(f"{row.para_id} did not pass {ner_filter_name}")

		if filtration_dict['total_paragraphs']% 100 == 0 or filtration_dict['total_paragraphs']== len(records):
			log.info(f'Number of paragraphs parsed so far: {filtration_dict["total_paragraphs"]}')
			log.info(f'Number of paragraphs with {property} information after heuristic filter: {len(records)}')
			log.info(f'Number of paragraphs with {property} information after NER filter ({ner_filter_name}) : {filtration_dict[f"{mode}_keyword_paragraphs_ner"]}')


	checkpoint.add_new(
		db, name = ner_filter_name, table = FilteredParagraphs.__tablename__,
		row = row.para_id, comment = {
			'user': sett.Run.userName, 'filter': ner_filter_name, 
			'debug': True if sett.Run.debugCount > 0 else False }
		)
	log.note(f'Last processed para_id: {row.para_id}')
	db.commit()

#!/usr/bin/env python
"""
Filter paragraphs for water transport-related content using NER model
"""

import os
import sys
import pylogg as log
from tqdm import tqdm
from collections import defaultdict

from backend import postgres, sett
from backend.postgres.orm import Papers, FilteredPapers, PaperTexts, FilteredParagraphs, PropertyMetadata
from backend.utils import checkpoint
import torch
from backend.record_extraction import bert_model

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

# Dictionary to track filtering statistics
filtration_dict = defaultdict(int)

material_entity_types = ['POLYMER', 'POLYMER_FAMILY', 'MONOMER', 'ORGANIC']

# Load NER model
if torch.cuda.is_available():
    log.info('GPU device found')
    device = 0
else:
    device = 'cpu'

# Load Materials bert to GPU
bert = bert_model.MaterialsBERT()
bert.init_local_model(
    sett.NERPipeline.model, device)
ner_pipeline = bert.pipeline

def add_to_filtered_paragraphs(para_id, ner_filter_name):
    """Add a paragraph to the filtered list if not already present"""
    paragraph = FilteredParagraphs().get_one(db, {'para_id': para_id, 'filter_name': ner_filter_name})
    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {para_id}. Skipped.")
        return False
    obj = FilteredParagraphs()
    obj.para_id = para_id
    obj.filter_name = ner_filter_name
    obj.insert(db)
    log.trace(f"Added to PostGres: {para_id}")
    return True

def ner_filter(para_text, unit_list=None, ner_output=None):
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
            prop_value_flag = True
    output_flag = mat_flag and prop_name_flag and prop_value_flag
    return ner_output, output_flag

def ner_filter_check(category, filter_name):
    """Main function to check paragraphs for water transport content using NER"""
    ner_filter_name = f"{filter_name}_ner"
    last_processed_id = checkpoint.get_last(db, name=ner_filter_name, table=PaperTexts.__tablename__)
    log.info("Last run row ID: {}", last_processed_id)

    query = '''
	SELECT fp.para_id, pt.text
	FROM filtered_paragraphs fp
	JOIN paper_texts pt ON fp.para_id = pt.id
	WHERE fp.filter_name = :filter_name
	AND fp.para_id > :last_processed_id ORDER BY fp.para_id LIMIT :limit;
	'''

    log.info("Querying list of non-processed paragraphs.")
    records = postgres.raw_sql(query, {'last_processed_id': last_processed_id, 'limit': 10000000, 'filter_name': filter_name})
    log.note("Found {} paragraphs not processed.", len(records))

    if len(records) == 0:
        return
    else:
        log.note("Unprocessed Row IDs: {} to {}", records[0].para_id, records[-1].para_id)

    relevant_paras = 0

    for row in tqdm(records):
        if row.para_id < last_processed_id:
            continue
        if sett.Run.debugCount > 0 and filtration_dict['total_paragraphs'] > sett.Run.debugCount:
            break
        filtration_dict['total_paragraphs'] += 1
        para = PaperTexts().get_one(db, {'id': row.para_id})
        ner_output, ner_filter_output = ner_filter(para_text=para.text)
        if ner_filter_output:
            log.note(f"{para.id} contains relevant {category} content (NER)")
            filtration_dict[f'{category}_paragraphs_ner'] += 1
            relevant_paras += 1
            if add_to_filtered_paragraphs(para_id=row.para_id, ner_filter_name=ner_filter_name):
                if relevant_paras % 20 == 0:
                    db.commit()
        else:
            log.info(f"{para.id} did not contain relevant {category} content (NER)")
        if filtration_dict['total_paragraphs'] % 100 == 0 or filtration_dict['total_paragraphs'] == len(records):
            log.info(f'Total paragraphs processed: {filtration_dict["total_paragraphs"]}')
            log.info(f'Paragraphs with {category} content (NER): {filtration_dict[f"{category}_paragraphs_ner"]}')
    log.info(f'Last processed para_id: {row.para_id}')
    checkpoint.add_new(db, name=ner_filter_name, table=PaperTexts.__tablename__, row=row.para_id,
                      comment={'user': sett.Run.userName, 'filter': ner_filter_name,
                              'debug': True if sett.Run.debugCount > 0 else False})
    db.commit()

def log_run_info(category, filter_name):
    """Log information about the current run"""
    t1 = log.note(f"{filter_name}_ner NER Filter Run for category: {category}")
    log.info("CWD: {}", os.getcwd())
    log.info("Host: {}", os.uname())
    if sett.Run.debugCount > 0:
        log.note("Debug run. Will parse maximum {} files.", sett.Run.debugCount)
    else:
        log.note("Production run. Will parse all files.")
    log.info("Using loglevel = {}", sett.Run.logLevel)
    return t1

if __name__ == '__main__':
    filter_name = 'water_transport_brandon'
    category = 'water_transport'
    os.makedirs(sett.Run.directory, exist_ok=True)
    log.setFile(open(sett.Run.directory + f"/{filter_name}_ner.log", "w+"))
    log.setLevel(sett.Run.logLevel)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)
    t1 = log_run_info(category, filter_name)
    ner_filter_check(category=category, filter_name=filter_name)
    t1.done("All Done.") 
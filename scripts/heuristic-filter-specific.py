#!/usr/bin/env python
"""
Filter paragraphs for thermoset-related content using specific keywords
"""

import os
import sys
import pylogg as log
from tqdm import tqdm
import argparse
from collections import defaultdict

from backend import postgres, sett
from backend.postgres.orm import Papers, FilteredPapers, PaperTexts, FilteredParagraphs
from backend.utils import checkpoint


sett.load_settings()
postgres.load_settings()
db = postgres.connect()

# Dictionary to track filtering statistics
filtration_dict = defaultdict(int)

THERMOSET_KEYWORDS = [
    'Thermoset',
    'Acrylate',
    'Methacrylate', 
    'Crosslinker',
    'PEGDA',
    'Thermomechanical',
    'UV',
    'BMA',
    '2-HEA',
    '2-HEMA',
    'TMPETA',
    'IBOA',
    'IDA',
    'BCOE',
    'DEGDMA',
    'Bisphenol A ethoxylate dimethacrylate',
    'EEMA'
]


WATER_TRANSPORT_KEYWORDS = [
    'Water Vapor',
    'water vapor separation',
    'water vapor activities',
    'water vapor activity', 
    'water permeability',
    'water vapor permeability',
    'water vapour permeability',
    'water diffusivity',
    'water diffusion',
    'water vapor diffusion',
    'water vapour diffusion',
    'water vapor diffusivity',
    'water vapour diffusivity',
    'water vapour diffusion coefficient',
    'water vapour solubility coefficient',
    'water vapor diffusion coefficient',
    'water vapor solubility coefficient',
    'water diffusion coefficient',
    'water permeability coefficient',
    'water solubility coefficient',
    'water solubility',
    'Water Vapor solubility',
    'Water Vapour solubility',
    'Water Vapor absorption',
    'Water Vapor adsorption', 
    'Water Vapor Sorption',
    'water sorption',
    'Water vapour absorption',
    'Water vapour adsorption',
    'Water vapour',
    'water vapour separation',
    'water vapour activities',
    'water vapour activity',
    'moisture permeation coefficient',
    'moisture solubility coefficient',
    'Moisture permeability',
    'Moisture diffusivity', 
    'Moisture diffusion',
    'solubility of water molecules',
    'diffusivity of water molecules'
]

SWELLING_KEYWORDS = [
    'Swelling degree',
    'Swelling ratio',
    'Uptake sorption',
    'Mass uptake',
    'Organic solvents',
    'Polymer solvent interaction parameter',
    'Flory Huggins interaction parameter',
    'Solubility'
]

def add_to_filtered_paragraphs(para_id, filter_name):
    """Add a paragraph to the filtered list if not already present"""
    paragraph = FilteredParagraphs().get_one(db, {'para_id': para_id, 'filter_name': filter_name})
    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {para_id}. Skipped.")
        return False
    
    obj = FilteredParagraphs()
    obj.para_id = para_id
    obj.filter_name = filter_name
    obj.insert(db)
    
    log.trace(f"Added to PostGres: {para_id}")
    return True

def keyword_filter(keyword_list, para):
    """Check if paragraph contains any keywords"""
    return any(keyword.lower() in para.text.lower() for keyword in keyword_list)

def process_keyword_content(para, category, KEYWORDS):
    """Process paragraph for thermoset content in specific category"""
    if keyword_filter(KEYWORDS, para):
        filtration_dict[f'{category}_paragraphs'] += 1
        return True
    return False

def keyword_filter_check(category, filter_name, KEYWORDS):
    """Main function to check paragraphs for thermoset content"""
    
    last_processed_id = checkpoint.get_last(db, name=filter_name, table=PaperTexts.__tablename__)
    log.info("Last run row ID: {}", last_processed_id)

    # Query to get paragraphs from thermoset papers
    query = '''
    SELECT pt.id AS para_id FROM paper_texts pt
    JOIN filtered_papers fp ON fp.doi = pt.doi
    WHERE pt.id > :last_processed_id
    AND fp.filter_name = 'polymer_papers'
    ORDER BY pt.id
    LIMIT :limit;
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

        # Fetch the paragraph text
        para = PaperTexts().get_one(db, {'id': row.para_id})

        if process_keyword_content(para, category, KEYWORDS):
            log.note(f"{para.id} contains relevant {category} content")
            relevant_paras += 1

            if add_to_filtered_paragraphs(para_id=row.para_id, filter_name=filter_name):
                if relevant_paras % 20 == 0:
                    db.commit()

        else:
            log.info(f"{para.id} did not contain relevant {category} content")

        if filtration_dict['total_paragraphs'] % 100 == 0 or filtration_dict['total_paragraphs'] == len(records):
            log.info(f'Total paragraphs processed: {filtration_dict["total_paragraphs"]}')
            log.info(f'Paragraphs with thermoset content: {filtration_dict[f"{category}_paragraphs"]}')
    
    log.info(f'Last processed para_id: {row.para_id}')

    checkpoint.add_new(db, name=filter_name, table=PaperTexts.__tablename__, row=row.para_id,
                      comment={'user': sett.Run.userName, 'filter': filter_name,
                              'debug': True if sett.Run.debugCount > 0 else False})
    
    db.commit()

def log_run_info(category, filter_name):
    """Log information about the current run"""
    t1 = log.note(f"{filter_name} Filter Run for category: {category}")
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
    keywords = WATER_TRANSPORT_KEYWORDS


    # parser = argparse.ArgumentParser(description='Run water transport filter')
    # parser.add_argument('--filter-name', '-f', required=True,
    #                   help='Name of the filter')
    # parser.add_argument('--category', '-c', required=True,
    #                   help='Category to filter for')
    # parser.add_argument('--keywords', '-k', required=True,
    #                   help='Keywords to filter for')
    
    # args = parser.parse_args()
    # filter_name = args.filter_name
    # category = args.category
    # keywords = args.keywords
    
    os.makedirs(sett.Run.directory, exist_ok=True)
    log.setFile(open(sett.Run.directory + f"/{filter_name}.log", "w+"))
    log.setLevel(sett.Run.logLevel)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)
    
    t1 = log_run_info(category, filter_name)
    keyword_filter_check(category=category, filter_name=filter_name, KEYWORDS=keywords)
    t1.done("All Done.") 
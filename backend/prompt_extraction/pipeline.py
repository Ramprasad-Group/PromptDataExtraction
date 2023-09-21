""" Entry point for LLM based data extraction and persistence. """

import pylogg
from backend.postgres.orm import PaperTexts
from backend.prompt_extraction.shot_selection import ShotSelector
from backend.prompt_extraction.prompt_extractor import LLMExtraction
from backend.prompt_extraction.material_extractor import MaterialExtractor
from backend.prompt_extraction.property_extractor import PropertyDataExtractor

log = pylogg.New('llm')


class LLMPipeline:
    def __init__(self, db, namelist_jsonl : str, prop_metadata_file : str,
                 extraction_info : dict, debug : bool = False) -> None:
        self.db = db
        self.debug = debug
        self.extraction_info = extraction_info
        self.material_extractor = MaterialExtractor(namelist_jsonl)
        self.property_extractor = PropertyDataExtractor(prop_metadata_file)

        self.llm = LLMExtraction(db, self.extraction_info)
        log.done("Initialized LLM extraction pipeline.")
        
    def run(self, paragraph : PaperTexts) -> int:
        """ Run the LLM pipeline on a given paragraph.
            Returns the number of records found.
        """
        records = []

        try:
            t2 = log.trace("Processing paragraph: {}", paragraph.id)
            records = self.llm.process_paragraph(paragraph)
            t2.done("LLM extracted records: {}", records)

        except Exception as err:
            log.error("Failed to run the LLM pipeline: {}", err)
            if self.debug: raise err
        
        if records is None:
            return 0
        else:
            extracted_records = self._parse_records(records)
            breakpoint()

        # Save to database.
        return 1


    def set_shot_selector(self, selector : ShotSelector):       
        self.extraction_info['shot_selector'] = str(selector)
        self.llm.shot_selector = selector
        self.llm.extraction_info = self.extraction_info


    def _parse_records(self, records : list) -> list:
        processed = []

        for record in records:
            material = self.material_extractor.parse_material(
                record['material'])

            value = self.property_extractor.parse_property(
                record['property'], record['value'])

            if material and value:
                processed.append({
                    'material': material,
                    'property': value,
                    'conditions': record['conditions']
                })

        return processed


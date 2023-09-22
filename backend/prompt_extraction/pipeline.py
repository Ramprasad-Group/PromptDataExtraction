""" Entry point for LLM based data extraction and persistence. """

import pylogg
from collections import namedtuple
from backend.postgres import persist
from backend.postgres.orm import PaperTexts
from backend.prompt_extraction.shot_selection import ShotSelector
from backend.prompt_extraction.prompt_extractor import LLMExtractor
from backend.prompt_extraction.crossref_extractor import CrossrefExtractor
from backend.prompt_extraction.material_extractor import MaterialExtractor
from backend.prompt_extraction.property_extractor import PropertyDataExtractor

log = pylogg.New('llm')

Record = namedtuple('Record', ['material', 'property', 'conditions'])

class LLMPipeline:
    def __init__(self, db, namelist_jsonl : str, prop_metadata_file : str,
                 extraction_info : dict, debug : bool = False) -> None:
        self.db = db
        self.debug = debug
        self.extraction_info = extraction_info
        self.crossref_extractor = CrossrefExtractor(db)
        self.material_extractor = MaterialExtractor(self.crossref_extractor,
                                                    namelist_jsonl)
        self.property_extractor = PropertyDataExtractor(db, prop_metadata_file)

        self.llm = LLMExtractor(db, self.extraction_info)
        self.extraction_info['prompt'] = self.llm.get_prompt()
        log.trace("Initialized {}", self.__class__.__name__)

    def run(self, paragraph : PaperTexts) -> int:
        """ Run the LLM pipeline on a given paragraph.
            Returns the number of records found.
        """
        newfound = 0
        records = []

        # Pre-process.
        try:
            t3 = log.trace("Preprocessing paragraph: {}", paragraph.id)
            self.crossref_extractor.process_paragraph(paragraph)
            t3.done("Preprocessing paragraph {}.", paragraph.id)
        except Exception as err:
            log.error("Failed to preprocess paragraph: {}", err)
            if self.debug: raise err
            return newfound

        # Extract.
        try:
            t2 = log.trace("Sending paragraph to LLM extractor: {}",
                           paragraph.id)
            records = self.llm.process_paragraph(paragraph)
            t2.done("LLM extraction, found {} records.", len(records))
        except Exception as err:
            log.error("Failed to run the LLM extractor: {}", err)
            if self.debug: raise err
            return newfound
        
        if not records:
            return newfound

        # Post-process and persist.
        try:
            t4 = log.trace("Post-processing LLM extracted records.")
            extracted_records = self._parse_records(records)
            newfound = self._save_records(paragraph, extracted_records)
            t4.done("Post-processing found {} valid records.",
                    len(extracted_records))
        except Exception as err:
            log.error("Failed to post-process LLM extracted records: {}", err)
            if self.debug: raise err
            return newfound

        return newfound


    def set_shot_selector(self, selector : ShotSelector):
        log.note("Using {} as shot selector.", selector)
        self.extraction_info['shot_selector'] = str(selector)
        self.llm.shot_selector = selector
        self.llm.extraction_info = self.extraction_info


    def _parse_records(self, llm_recs : list) -> list[Record]:
        processed = []

        for rec in llm_recs:
            material = self.material_extractor.parse_material(
                rec['material'])

            value = self.property_extractor.parse_property(
                rec['property'], rec['value'])

            if material and value:
                processed.append(Record(material=material, property=value,
                                        conditions=rec['conditions']))
        return processed


    def _save_records(self, para : PaperTexts, records : list[Record]) -> int:
        m = 0
        p = 0
        for record in records:
            if persist.add_material(self.db, para, self.extraction_info,
                                    record.material):
                m += 1

            if persist.add_property(self.db, para, self.extraction_info,
                                    record.material, record.property,
                                    record.conditions):
                p += 1

        # Save.
        self.db.commit()
        self.db.close()
        log.done("Database added: {} new materials, {} new records.", m, p)
        return p
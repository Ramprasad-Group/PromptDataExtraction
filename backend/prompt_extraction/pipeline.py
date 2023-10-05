""" Entry point for LLM based data extraction and persistence. """
import os
import pylogg
from collections import namedtuple
from backend.postgres import persist
from backend.postgres.orm import PaperTexts, ExtractionMethods
from backend.prompt_extraction.prompt_extractor import LLMExtractor
from backend.prompt_extraction.crossref_extractor import CrossrefExtractor
from backend.prompt_extraction.material_extractor import MaterialExtractor
from backend.prompt_extraction.property_extractor import PropertyDataExtractor
from backend.prompt_extraction.shot_selection import (
    RandomShotSelector, DiverseShotSelector, SimilarShotSelector
)
from backend.prompt_extraction.tokenizers import BertTokenizer

log = pylogg.New('llm')

Record = namedtuple('Record', ['material', 'property', 'condition'])


class LLMPipeline:
    def __init__(self, db, method : ExtractionMethods, outdir : str,
                 namelist_jsonl : str, prop_metadata_file : str) -> None:
        self.db = db
        self.method = method
        self.outdir = outdir
        self.crossref_extractor = CrossrefExtractor(db)
        self.material_extractor = MaterialExtractor(self.crossref_extractor,
                                                    namelist_jsonl)
        self.property_extractor = PropertyDataExtractor(db, prop_metadata_file)

        self.llm = LLMExtractor(db, self.method)
        log.trace("Initialized {}", self.__class__.__name__)


    def init_shot_selector(self, bert_model_path : str,
                           pytorch_device : int = 0, rebuild : bool = False):

        # Get the required params from the method definition.
        nshots = self._get_param('n_shots', 1)
        shot_selector = self._get_param('shot_selector', None)
        shot_min_recs = self._get_param('shot_nrecords', 2)
        shot_keywords = self._get_param('shot_keywords', False)

        if shot_selector is None:
            log.critical("shot_selector is not defined by the method.")
            raise ValueError("Shot selector needed.")
        else:
            if not nshots:
                log.warn("Shot selector defined, but using zero shots.")
                return

        # Initialize shot sampler.
        shot_curated_dataset = os.path.join(self.outdir, "shots.json")
        shot_embeddings_file = os.path.join(self.outdir, "embeddings.json")

        if shot_selector == 'random':
            self.llm.shot_selector = RandomShotSelector(shot_min_recs)

        elif shot_selector == 'diverse':
            tokenizer = BertTokenizer(bert_model_path, pytorch_device)
            self.llm.shot_selector = \
                DiverseShotSelector(tokenizer, shot_min_recs, shot_keywords)

        elif shot_selector == 'similar':
            tokenizer = BertTokenizer(bert_model_path, pytorch_device)
            self.llm.shot_selector = \
                SimilarShotSelector(tokenizer, shot_min_recs, shot_keywords)

        else:
            log.critical("Invalid shot selector: {}", shot_selector)
            raise ValueError("Invalid shot selector", shot_selector)

        self.llm.shot_selector.build_curated_dataset(
            self.db, shot_curated_dataset, rebuild)
        
        self.llm.shot_selector.compute_embeddings(shot_embeddings_file,
                                                  rebuild)

        # Update the missing fields with the default values.
        self.db.commit()

        log.note("Using {} with {} shots.", self.llm.shot_selector, nshots)


    def run(self, paragraph : PaperTexts) -> int:
        """ Run the LLM pipeline on a given paragraph.
            Returns the number of records found.
        """

        # Pre-process.
        t3 = log.trace("Preprocessing paragraph: {}", paragraph.id)
        self.crossref_extractor.process_paragraph(paragraph)
        t3.done("Preprocessing paragraph {}.", paragraph.id)

        # Extract via API.
        t2 = log.trace("Sending paragraph to LLM extractor: {}",
                        paragraph.id)
        records, reqid = self.llm.process_paragraph(paragraph)
        t2.done("LLM extraction, found {} records.", len(records))
        
        if not records:
            return 0

        # Post-process and save to db.
        t4 = log.trace("Post-processing LLM extracted records.")
        extracted = self._parse_records(records)
        newfound = self._save_records(paragraph, extracted, reqid)
        t4.done("Post-processing found {} new valid records.", len(extracted))

        return newfound


    def _get_param(self, name, default):
        """ Get the value of a field of the method's extraction_info. """
        info = dict(self.method.extraction_info)
        if name not in info:
            info[name] = default
            # Assignment required for sqlalchemy dict updates.
            self.method.extraction_info = info
        return info[name]
    

    def _parse_records(self, llm_recs : list) -> list[Record]:
        processed = []

        for rec in llm_recs:
            material = self.material_extractor.parse_material(
                rec['material'])

            value = self.property_extractor.parse_property(
                rec['property'], rec['value'])

            if material and value:
                processed.append(Record(material=material,
                                        property=value,
                                        condition=rec['condition']))

        return processed


    def _save_records(self, para : PaperTexts, records : list[Record],
                      api_req_id : int) -> int:
        m = 0
        p = 0

        for record in records:
            if persist.add_material(
                self.db, para, self.method, record.material):
                m += 1

            if persist.add_property(
                self.db, para, self.method, record.material, record.property,
                api_req_id=api_req_id, extracted_condition=record.condition):
                p += 1

        # Save.
        self.db.commit()
        self.db.close()

        log.done("Database added: {} new materials, {} new records.", m, p)
        return p

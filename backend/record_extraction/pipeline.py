import pylogg
from backend.postgres import persist
from backend.postgres.orm import PaperTexts, ExtractionMethods
from backend.record_extraction import record_extractor, bert_model, base_classes

log = pylogg.New('ner')


class NERPipeline:
    def __init__(self, db, method : ExtractionMethods,
                 bert : bert_model.MaterialsBERT, nendata_json : str,
                 prop_metadata_file : str, debug : bool = False) -> None:
        self.db = db
        self.debug = debug
        self.method = method
        self.bert = bert
        self.norm_dataset = nendata_json
        self.prop_meta_file = prop_metadata_file
        log.trace("Initialized {}", self.__class__.__name__)


    def run(self, paragraph : PaperTexts) -> int:
        """ Run the NER pipeline on a given paragraph.
            Returns the number of records found.
        """
        t2 = log.trace("Processing paragraph.")
        newfound = 0
        records = []

        # Get the output dictionary.
        ner_output = self._extract_data(paragraph.text)
        if ner_output is False:
            log.info("Text is not relevant, no output.")
            return

        # polymer_families = ner_output.get("polymer_family", [])
        # monomers = ner_output.get("monomers", [])

        records = ner_output.get("material_records", [])
        log.info("Found {} records.", len(records))

        newfound = self._save_records(paragraph, records)
        t2.done("Paragraph {} processed: {} records.",
                paragraph.id, len(records))
        
        return newfound


    def _extract_data(self, text : str) -> dict:
        """ Extract data from a text by passing through the materials bert
            NER pipeline.

            Returns the extracted dictionary of polymer family, monomers,
            and records containing materials, amounts, properties etc.
        """
        ner_tags = self.bert.get_tags(text)
        relation_extractor = record_extractor.RelationExtraction(
            text, ner_tags, self.norm_dataset, self.prop_meta_file)
        output_para, timings = relation_extractor.process_document()
        return output_para


    def _get_material_list(self, items) -> list:
        """ Normalize the return data of the NER pipeline. """
        if items is None:
            return []
        elif type(items) == list:
            return items
        elif type(items) == dict:
            return [ base_classes.MaterialMention(**items) ]
        else:
            return [i for i in items.entity_list]


    def _get_amount_list(self, items) -> list:
        """ Normalize the return data of the NER pipeline. """
        if items is None:
            return []
        elif type(items) == list:
            return items
        elif type(items) == dict:
            return [ base_classes.MaterialAmount(**items) ]
        else:
            return [i for i in items.entity_list]


    def _save_records(self, paragraph : PaperTexts, records : list) -> int:
        m, p, a = 0, 0, 0

        # Insert the materials first.
        for rec in records:
            materials_list = self._get_material_list(rec.get('material_name'))
            for material in materials_list:
                if persist.add_material(
                    self.db, paragraph, self.method, material):
                    m += 1

        for rec in records:
            materials_list = self._get_material_list(rec.get('material_name'))
            amount_list = self._get_amount_list(rec.get('material_amount'))

            for amount in amount_list:
                if persist.add_material_amount(
                    self.db, paragraph, self.method, amount):
                    a += 1

            # dict
            prop = rec.get('property_record', {})

            # Generally we expect to have only one material for a property dict.
            # But there can be multiple in the materials in the list sometimes.
            for material in materials_list:
                if persist.add_property(
                    self.db, paragraph, self.method, material, prop):
                    p += 1

        self.db.commit()
        self.db.close()
        log.done("Database new added: {} materials, {} amounts, {} records.",
                 m, a, p)
        return p


import pylogg
from backend.postgres import persist
from backend.postgres.orm import PaperTexts, ExtractionMethods
from backend.record_extraction import record_extractor, bert_model, base_classes

log = pylogg.New('ner')


class NERPipeline:
    def __init__(self, db, method : ExtractionMethods,
                 bert : bert_model.MaterialsBERT, nendata_json : str,
                 prop_metadata_file : str) -> None:
        self.db = db
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


    def _get_material_list(self, items) -> list[base_classes.MaterialMention]:
        """ Normalize the return data of the NER pipeline. """
        if items is None:
            return []
        elif type(items) == list:
            return items
        elif type(items) == dict:
            return [ base_classes.MaterialMention(**items) ]
        else:
            return [i for i in items.entity_list]


    def _get_amount_list(self, items) -> list[base_classes.MaterialAmount]:
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
        m, p, a, r = 0, 0, 0, 0

        # Insert the items first.
        for rec in records:
            # Insert the amounts.
            amount_list = self._get_amount_list(rec.get('material_amount'))
            for amount in amount_list:
                if not amount.entity_name:
                    continue
                if persist.add_material_amount(
                    self.db, paragraph, self.method, amount):
                    a += 1

            # Insert the materials, store their IDs in a map.
            matids = {}
            materials_list = self._get_material_list(rec.get('material_name'))

            # Get rid of the ones with empty name.
            materials_list = [m for m in materials_list if m.entity_name]

            # Empty list of materials.
            if not materials_list:
                continue

            for material in materials_list:
                matid = persist.add_material(self.db, paragraph, self.method,
                                             material)
                if matid:
                    matids[material.entity_name] = matid
                    m += 1


            prop = rec.get('property_record', {})

            # Emptry property.
            if not prop.entity_name:
                continue

            # Insert the property with the last material.
            propid = persist.add_property(self.db, paragraph, self.method,
                                          material, prop)
            if propid:
                p += 1

                # Insert one to many relationships for all materials.
                for material in materials_list:
                    matid = matids[material.entity_name]
                    relid = persist.add_material_property_rel(
                        self.db, matid, propid, self.method.id)

                    if relid: r += 1

            # Confirm saving the record.
            self.db.commit()

        log.info("Database new added: {} materials, {} amounts, {} properties, "
                 "{} relations.", m, a, p, r)
        return p


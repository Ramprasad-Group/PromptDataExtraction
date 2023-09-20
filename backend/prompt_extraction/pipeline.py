""" Entry point for LLM based data extraction and persistence. """

import pylogg
from backend.prompt_extraction import prompt_extractor
from backend.prompt_extraction.material_extractor import MaterialNameExtractor
from backend.prompt_extraction.shot_selection import ShotSelector
from backend.postgres.orm import (
    PaperTexts, ExtractedMaterials, ExtractedProperties,
)

log = pylogg.New('llm')


class LLMPipeline:
    def __init__(self, db, namelist_jsonl : str,
                 extraction_info : dict, debug : bool = False) -> None:
        self.db = db
        self.debug = debug
        self.extraction_info = extraction_info
        self.material_extractor = MaterialNameExtractor(namelist_jsonl)

        self.llm = prompt_extractor.LLMExtraction(db, self.extraction_info)
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
            records = self._parse_records(records)
        
        return len(records)


    def set_shot_selector(self, selector : ShotSelector):       
        self.extraction_info['shot_selector'] = str(selector)
        self.llm.shot_selector = selector
        self.llm.extraction_info = self.extraction_info


    def _parse_records(self, records : list) -> list:
        processed = []

        for record in records:
            record['material'] = \
                self.material_extractor.parse_material(record['material'])
            record['property'] = self._parse_property(
                record['property'], record['value'])           
            processed.append(record)

        return processed


def process_output(db, paragraph: PaperTexts,
                   llm_output : list[dict], extraction_info: dict):

    """ Store the LLM output data to database. """

    if llm_output is None:
        log.error("None LLM output.")
        return

    # We need to insert and commit the materials first.
    for rec in llm_output:
        material = rec.get('material', None)
        if material:
            add_material_to_postgres(db, extraction_info, paragraph, material)

    db.commit()

    for rec in llm_output:
        material = rec.get('material', None)
        if material:
            prop = rec.get('property', None)
            if prop:
                add_property_to_postgres(
                    db, extraction_info, paragraph, material, prop)


def get_material(db, para_id: int, material_name: str) -> ExtractedMaterials:
    """ Return an extracted material object using a para id and entity name.
        Returns None if not found.
    """
    return ExtractedMaterials().get_one(db, {
        'para_id': para_id,
        'entity_name': material_name
    })


def add_material_to_postgres(
        db, extraction_info: dict,
        paragraph: PaperTexts, material: dict) -> bool:
    """ Add an extracted material entry to postgres.
        Check uniqueness based on para id and material entity name.

        Returns true if the row was added to db.
    """

    assert type(material) == dict

    entity_name = material.get('entity_name')
    if not entity_name:
        return False

    # check if already exists
    if get_material(db, paragraph.id, entity_name):
        return False

    matobj = ExtractedMaterials()
    matobj.para_id = paragraph.id
    matobj.entity_name = entity_name
    matobj.extraction_info = extraction_info
    matobj.normalized_material_name = \
        material.get('normalized_material_name', '')
    matobj.material_class = ''
    matobj.polymer_type = ''
    matobj.coreferents = []
    matobj.components = []
    matobj.additional_info = {}

    role = material.get('role')
    if role:
        matobj.additional_info.update({
            'material_role': role
        })

    matobj.insert(db)
    return True


def add_property_to_postgres(
        db, extraction_info: dict,
        paragraph: PaperTexts, material_map: dict, property: dict) -> bool:
    """ Add an extracted material property values to postgres.
        Check uniqueness based on material id and property entity name.

        Returns true if the row was added to db.
    """
    assert type(property) == dict

    material_name = material_map.get('entity_name')
    if not material_name:
        return False

    # Make sure it's a number or ignore.
    numeric_value = property.get('property_numeric_value')
    try:
        numeric_value = float(numeric_value)
    except:
        return False

    material = get_material(db, paragraph.id, material_name)
    if material is None:
        log.warn("Material {} not found in extracted_materials "
                 "to store properties.", material_name)
        return False

    # check if already exists
    if ExtractedProperties().get_one(db, {
        'material_id': material.id,
        'entity_name': property.get('entity_name', None),
        'numeric_value': numeric_value,
    }):
        return False

    propobj = ExtractedProperties()
    propobj.material_id = material.id
    propobj.entity_name = property.get('entity_name')
    propobj.value = property.get('property_value')
    propobj.coreferents = []
    propobj.numeric_value = numeric_value
    propobj.numeric_error = property.get('property_numeric_error')
    propobj.value_average = property.get('property_value_avg')
    propobj.value_descriptor = property.get('property_value_descriptor')
    propobj.unit = property.get('property_unit')

    propobj.extraction_info = extraction_info

    propobj.conditions = {}
    tcond = property.get('temperature_condition', None)
    if tcond:
        propobj.conditions.update({'temperature_condition': tcond})

    fcond = property.get('frequency_condition', None)
    if fcond:
        propobj.conditions.update({'frequency_condition': fcond})

    propobj.insert(db)
    return True

import os
import sys
import pylogg as log

from backend import postgres, sett
from backend.utils.frame import Frame
from backend.postgres.orm import (
    PaperTexts, FilteredParagraphs,
    ExtractedMaterials, ExtractedAmount, ExtractedProperties,
)

from backend.data.dataset_pranav import GroundDataset
from backend.record_extraction import bert_model, record_extractor, utils

def extract_data(text) -> dict:
    """ Extract data from a text by passing through the materials bert
        NER pipeline.

        Returns the extracted dictionary of polymer family, monomers,
        and records containing materials, amounts, properties etc.
    """
    ner_tags = bert.get_tags(text)
    relation_extractor = record_extractor.RelationExtraction(
        text, ner_tags, norm_dataset, prop_metadata)
    output_para, timings = relation_extractor.process_document()
    return output_para


def get_material(para_id : int, material_name : str) -> ExtractedMaterials:
    """ Return an extracted material object using a para id and entity name.
        Returns None if not found.
    """
    return ExtractedMaterials().get_one(db, {
        'para_id': para_id,
        'entity_name': material_name
    })


def add_material_to_postgres(
        paragraph : PaperTexts, material : dict) -> bool:
    """ Add an extracted material entry to postgres.
        Check uniqueness based on para id and material entity name.

        Returns true if the row was added to db.
    """

    assert type(material) == dict

    entity_name = material.get('entity_name')
    if not entity_name:
        return False

    # check if already exists
    if get_material(paragraph.id, entity_name):
        return False
    
    if material['components']:
        log.debug("Components: {}", material['components'])
        breakpoint()

    matobj = ExtractedMaterials()
    matobj.para_id = paragraph.id
    matobj.entity_name = entity_name
    matobj.material_class = material.get('material_class', '')
    matobj.polymer_type = material.get('polymer_type')
    matobj.normalized_material_name = material.get('normalized_material_name')
    matobj.coreferents = list(material.get('coreferents'))
    matobj.components = list(material.get('components'))
    matobj.additional_info = {}

    role = material.get('role')
    if role:
        matobj.additional_info.update({
            'material_role': role
        })

    matobj.insert(db)
    return True


def add_amount_to_postgres(
        paragraph : PaperTexts, amount : dict) -> bool:
    """ Add an extracted material amount entry to postgres.
        Check uniqueness based on material id and material entity name.

        Returns true if the row was added to db.
    """
    if type(amount) != dict:
        return False

    name : str = amount.get('entity_name', None)
    if not name:
        return False
    
    # check if already exists
    if ExtractedAmount().get_one(db, {
        'para_id': paragraph.id,
        'entity_name': name
    }):
        return False


    amtobj = ExtractedAmount()
    amtobj.para_id = paragraph.id
    amtobj.entity_name = name
    amtobj.material_amount = amount.get('material_amount')

    amtobj.insert(db)
    return True


def add_property_to_postgres(
        paragraph : PaperTexts,
        material_map : dict, property : dict) -> bool:
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

    material = get_material(paragraph.id, material_name)
    if material is None:
        log.warn("Material {} not found in extracted_materials "
                 "to store properties.", material_name)
        return False

    # check if already exists
    if ExtractedProperties().get_one(db,{
        'material_id': material.id,
        'entity_name': property.get('entity_name', None),
        'numeric_value': numeric_value,
    }):
        return False

    propobj = ExtractedProperties()
    propobj.material_id = material.id
    propobj.entity_name = property.get('entity_name')
    propobj.value = property.get('property_value')
    propobj.coreferents = list(property.get('coreferents'))
    propobj.numeric_value = numeric_value
    propobj.numeric_error = property.get('property_numeric_error')
    propobj.value_average = property.get('property_value_avg')
    propobj.value_descriptor = property.get('property_value_descriptor')
    propobj.unit = property.get('property_unit')

    propobj.extraction_method = 'materials-bert'

    propobj.conditions = {}
    tcond = property.get('', None)
    if tcond:
        propobj.conditions.update({'temperature_condition': tcond})

    fcond = property.get('frequency_condition', None)
    if fcond:
        propobj.conditions.update({'frequency_condition': fcond})

    propobj.insert(db)
    return True


def process_paragraph(paragraph : PaperTexts):
    """ Extract data from an individual paragraph object. """
    t2 = log.trace("Processing paragraph.")
    # Get the paragraph text
    text = paragraph.text

    # Get the output object
    ner_output = extract_data(text)

    if ner_output is False:
        log.trace("Text is not relevant, not output.")
        return

    polymer_families = ner_output.get("polymer_family", [])
    monomers = ner_output.get("monomers", [])
    records = ner_output.get("material_records", [])

    log.trace("Found {} records.", len(records))

    # We need to insert and commit the materials first.
    for rec in records:
        # list of dicts
        materials_list = rec.get("material_name", [])
        for material in materials_list:
            add_material_to_postgres(paragraph, material)

    db.commit()

    for rec in records:
        # list of dicts
        materials_list = rec.get("material_name", [])

        # list of dicts
        for amount in rec.get('material_amount', []):
            add_amount_to_postgres(paragraph, amount)

        # dict
        prop = rec.get('property_record', {})

        # Generally we expect to have only one material for a property dict.
        # But there can be multiple in the materials list sometimes.
        for material in materials_list:
            add_property_to_postgres(paragraph, material, prop)
    
    t2.done("Paragraph processed.")


def run_pipeline(debugCount):
    # Make sure we are not processing previously processed paragraphs.
    # Get the last para id added to DB.
    pass

def test_ground_dataset(debugCount, mode = 'Tg'):
    # Tg and/or bandgap curated ground datasets.
    t2 = log.trace("Loading ground dataset.")
    gnd = GroundDataset()
    tg_gnd, tg_nlp = gnd.create_dataset(mode)
    t2.done("Loaded ground dataset.")

    abstract = None
    n = 0
    for doi, value in tg_gnd.items():
        n += 1
        if debugCount > 0 and n > debugCount:
            break

        print(n, doi)
        abstract = [item['abstract'] for item in value if item['abstract'] != ''][0]
        if debugCount > 0:
            print(abstract)

        paragraph = PaperTexts()
        paragraph.id = n
        paragraph.pid = 1
        paragraph.directory = 'ground_dataset'
        paragraph.doctype = 'csv'
        paragraph.doi = doi
        paragraph.text = abstract

        process_paragraph(paragraph)


def init_logger():
    """
        Log run information for reference purposes.
        Returns a log Timer.
    """
    os.makedirs(sett.Run.directory, exist_ok=True)

    t1 = log.init(
        log_level=sett.Run.logLevel,
        output_directory=sett.Run.directory
    )

    if sett.Run.debugCount > 0:
        log.note("Debug run. Will process maximum {} items.",
                 sett.Run.debugCount)
    else:
        log.info("Production run. Will process all items.")

    if not sett.FullTextParse.add2postgres:
        log.warn("Will not be adding to postgres.")
    else:
        log.info("Will be adding extracted data to postgres.")

    return t1


if __name__ == '__main__':
    sett.load_settings()
    t1 = init_logger()

    # Load NEN dataset and property metadata.
    normdata = utils.LoadNormalizationDataset(sett.DataFiles.polymer_nen_json)
    norm_dataset = normdata.process_normalization_files()
    prop_metadata = utils.load_property_metadata(sett.DataFiles.properties_json)

    # Connect to database    
    postgres.load_settings()
    db = postgres.connect()

    # Load Materials bert to GPU
    bert = bert_model.MaterialsBERT(sett.NERPipeline.model)
    bert.init_local_model(device=sett.NERPipeline.pytorch_device)

    # run_pipeline(sett.Run.debugCount)
    test_ground_dataset(sett.Run.debugCount, mode='bandgap')

    t1.done("All Done.")
    log.close()

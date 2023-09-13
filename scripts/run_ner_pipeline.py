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
    relation_extractor = record_extractor.RelationExtraction(text, ner_tags, norm_dataset, prop_metadata)
    output_para, timings = relation_extractor.process_document()
    return output_para


def get_material(para_id : int, material_name : str):
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

    # check if already exists
    if get_material(paragraph.id, material.get('entity_name')):
        return False

    matobj = ExtractedMaterials()
    matobj.para_id = paragraph.id
    matobj.entity_name = material.get('entity_name')
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
    assert type(amount) == dict

    name : str = amount.get('entity_name', None)

    if not name:
        return False
    
    # The material entity name may not exist in the materials table.
    material = get_material(paragraph.id, name)
    if material is None:
        if not name.startswith("poly"):
            name = "poly" + name
            material = get_material(paragraph.id, name)
            if material is None:
                log.warn("Material not found in extracted_materials "
                         "to store amount: {}.", amount)
                return False
        else:
            name = name.lstrip("poly")
            material = get_material(paragraph.id, name)
            if material is None:
                log.warn("Material not found in extracted_materials "
                         "to store amount:", amount)
                return False

    # check if already exists
    if ExtractedAmount().get_one(db,{
        'material_id': material.id,
        'material_amount': amount.get('material_amount')
    }):
        return False


    amtobj = ExtractedAmount()
    amtobj.material_id = material.id
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
    material = get_material(paragraph.id, material_name)
    if material is None:
        log.warn("Material {} not found in extracted_materials "
                 "to store properties.", material_name)
        return False

    # check if already exists
    if ExtractedProperties().get_one(db,{
        'material_id': material.id,
        'entity_name': property.get('entity_name', None),
    }):
        return False

    propobj = ExtractedProperties()
    propobj.material_id = material.id
    propobj.entity_name = property.get('entity_name')
    propobj.value = property.get('property_value')
    propobj.coreferents = list(property.get('coreferents'))
    propobj.numeric_value = property.get('property_numeric_value')
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


def debug_single_para(para_id : int):
    paragraph = PaperTexts()
    paragraph.id = 1
    paragraph.pid = 1
    paragraph.directory = 'test'
    paragraph.doctype = 'html'
    paragraph.doi = '10.1039/c6gc03238a'
    paragraph.text = """
    The general and efficient copolymerization of lactones with hydroxy-acid bioaromatics was accomplished via a concurrent ring-opening polymerization (ROP) and polycondensation methodology. Suitable lactones were L-lactide or ε-caprolactone and four hydroxy-acid comonomers were prepared as hydroxyethyl variants of the bioaromatics syringic acid, vanillic acid, ferulic acid, and p-coumaric acid. Copolymerization conditions were optimized on a paradigm system with a 20:80 feed ratio of caprolactone:hydroxyethylsyringic acid. Among six investigated catalysts, polymer yield was optimized with 1 mol % of Sb_{2}O_{3}, affording eight copolymer series in good yields (32-95 % for lactide; 80-95 % for caprolactone). Half of the polymers were soluble in the GPC solvent hexafluoroisopropanol and analyzed to high molecular weight, with M_{n} = 10500-60700 Da. Mass spectrometry and ^{1}H NMR analysis revealed an initial ring-opening formation of oligolactones, followed by polycondensation of these with the hydroxy-acid bioaromatic, followed by transesterification, yielding a random copolymer. By copolymerizing bioaromatics with L-lactide, the glass transition temperature (T_{g}) of polylactic acid (PLA, 50 °C) could be improved and tuned in the range of 62-107 °C; the thermal stability (T_{95 %}) of PLA (207 °C) could be substantially increased up to 323 °C. Similarly, bioaromatic incorporation into polycaprolactone (PCL, T_{g} = -60 °C) accessed an improved T_{g} range from -48 to 105 °C, while exchanging petroleum-based content with biobased content. Thus, this ROP/polycondensation methodology yields substantially or fully biobased polymers with thermal properties competitive with incumbent packaging thermoplastics such as polyethylene terephthalate (T_{g} = 67 °C) or polystyrene (T_{g} = 95 °C).
    """

    process_paragraph(paragraph)
    db.commit()


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
        log.note("Debug run. Will parse maximum {} files.",
                 sett.Run.debugCount)
    else:
        log.note("Production run. Will parse all files in {}",
                 sett.FullTextParse.paper_corpus_root_dir)

    if not sett.FullTextParse.add2postgres:
        log.warn("Will not be adding to postgres.")
    else:
        log.note("Will be adding extracted data to postgres.")

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

    # Tg and/or bandgap curated ground datasets.
    # gnd = GroundDataset()
    # tg_gnd, tg_nlp = gnd.create_dataset()

    if len(sys.argv) > 1:
        debug_single_para(int(sys.argv[1]))
    else:
        run_pipeline(sett.Run.debugCount)


    t1.done("All Done.")
    log.close()

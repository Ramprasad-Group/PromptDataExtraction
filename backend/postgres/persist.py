import pylogg
from backend.record_extraction.base_classes import (
    MaterialMention, PropertyValuePair
)
from . import orm

log = pylogg.New("persist")

def add_crossref(db, para : orm.PaperTexts, name : str, othername : str,
                   reftype : str) -> bool :
    """ Add a cross reference to the database.
        Returns false if already exists.
    """
    # log.debug("Adding {} cross-ref for paper {}: {} = {}",
    #           reftype, para.pid, name, othername)
    
    ref = orm.ExtractedCrossrefs().get_one(
        db, {'name': name, 'reftype': reftype})

    if ref is None:
        ref = orm.ExtractedCrossrefs()
        ref.paper_id = para.pid
        ref.para_id = para.id
        ref.name = name
        ref.othername = othername
        ref.reftype = reftype

        ref.insert(db)
        return True
    
    return False


def add_method(db, name : str, dataset : str, model : str,
                   api : str = None, para_subset : str = None,
                   **kwargs) -> bool:
    """ Add a new method by inserting and committing
        a new row id to the extraction_methods.
        
        db:         PostGres scoped session object.
        name:       Name of the data extraction method/pipeline.
        dataset:    Name of the extracted dataset.
        model:      Model used for data extraction, eg. materials-bert.
        api:        API used for the data extraction, eg. openai.
        para_subset:
                    Name of the paragraph filter (from the filtered_paragraphs)
                    if any.
        **kwargs:   Any other additional info, e.g. username etc.

        Returns True if successful, False if name already exists.
    """

    t2 = log.info(f"New Method. Name: {name}, Dataset: {dataset}, "
                  f"Model: {model}, API: {api}, Paras: {para_subset}")
    
    if get_method(db, name=name):
        log.error("Method {} already exists.", name)
        return False

    method = orm.ExtractionMethods()
    method.name = name
    method.dataset = dataset
    method.model = model
    method.api = api
    method.para_subset = para_subset
    method.extraction_info = kwargs
    
    method.insert(db)
    db.commit()
    t2.done("New method added: {}", name)
    return True

def get_method(db, **kwargs) -> orm.ExtractionMethods:
    """ Return an Extraction Method object using specified column values.
        Available columns:
            name, dataset, model, api, para_subset.
    """
    return orm.ExtractionMethods().get_one(db, kwargs)


def get_material(db, para_id: int, material_name: str,
                 method : orm.ExtractionMethods) -> orm.ExtractedMaterials:
    """ Return an extracted material object using a para id and material name.
        Returns None if not found.
    """
    return orm.ExtractedMaterials().get_one(db, {
        'para_id': para_id,
        'method_id': method.id,
        'entity_name': material_name
    })


def add_material(db, para : orm.PaperTexts, method : orm.ExtractionMethods,
                 material : MaterialMention) -> bool:

    assert type(material) == MaterialMention

    entity_name = material.entity_name
    if not entity_name:
        return False

    # check if already exists
    if get_material(db, para.id, entity_name, method):
        return False

    if material.components:
        log.debug("Components: {}", material.components)

    matobj = orm.ExtractedMaterials()
    matobj.para_id = para.id
    matobj.method_id = method.id
    matobj.entity_name = entity_name
    matobj.material_class = material.material_class
    matobj.polymer_type = material.polymer_type
    matobj.normalized_material_name = material.normalized_material_name
    matobj.coreferents = list(material.coreferents)
    matobj.components = list(material.components)
    matobj.additional_info = {}
    matobj.extraction_info = {}

    if material.role:
        matobj.additional_info.update({
            'material_role': material.role
        })

    matobj.insert(db)
    return True


def add_property(db, para : orm.PaperTexts, method : orm.ExtractionMethods,
                 material : MaterialMention, prop : PropertyValuePair,
                 conditions : str = "", details : dict = {}) -> bool:
    """ Add extracted properties values to postgres.
        Check uniqueness based on material id and property entity name,
        and numeric value.
        Returns true if the row was added to db.
    """
    assert type(material) == MaterialMention
    assert type(prop) == PropertyValuePair

    material_name = material.entity_name
    if not material_name:
        return False

    # Make sure it's a number or ignore.
    numeric_value = prop.property_numeric_value
    try:
        numeric_value = float(numeric_value)
    except:
        return False

    material = get_material(db, para.id, material_name, method)
    if material is None:
        log.error("Material {} not found in extracted_materials "
                 "to store properties.", material_name)
        return False

    # check if already exists
    if orm.ExtractedProperties().get_one(db, {
        'material_id': material.id,
        'method_id': method.id,
        'entity_name': prop.entity_name,
        'numeric_value': numeric_value
    }):
        return False

    propobj = orm.ExtractedProperties()
    propobj.material_id = material.id
    propobj.method_id = method.id
    propobj.entity_name = prop.entity_name
    propobj.value = prop.property_value
    propobj.coreferents = list(prop.coreferents)
    propobj.numeric_value = numeric_value
    propobj.numeric_error = prop.property_numeric_error
    propobj.value_average = prop.property_value_avg
    propobj.value_descriptor = prop.property_value_descriptor
    propobj.unit = prop.property_unit
    propobj.extraction_info = {}

    # Copy here. Or, dicts and lists params will persist between function calls.
    propobj.conditions = dict(details)
    tcond = prop.temperature_condition
    if tcond:
        propobj.conditions['temperature_condition'] = tcond

    fcond = prop.frequency_condition
    if fcond:
        propobj.conditions['frequency_condition'] = fcond

    if conditions:
        propobj.conditions['extracted'] = conditions

    if prop.condition_str:
        propobj.conditions['measurement'] = prop.condition_str

    propobj.insert(db)
    return True

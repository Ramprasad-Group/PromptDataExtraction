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


def get_material(db, para_id: int, material_name: str) -> orm.ExtractedMaterials:
    """ Return an extracted material object using a para id and material name.
        Returns None if not found.
    """
    return orm.ExtractedMaterials().get_one(db, {
        'para_id': para_id,
        'entity_name': material_name
    })


def add_material(db, para : orm.PaperTexts, extraction_info : dict,
                 material : MaterialMention) -> bool:

    assert type(material) == MaterialMention

    entity_name = material.entity_name
    if not entity_name:
        return False

    # check if already exists
    if get_material(db, para.id, entity_name):
        return False

    if material.components:
        log.debug("Components: {}", material.components)

    matobj = orm.ExtractedMaterials()
    matobj.para_id = para.id
    matobj.entity_name = entity_name
    matobj.material_class = material.material_class
    matobj.polymer_type = material.polymer_type
    matobj.normalized_material_name = material.normalized_material_name
    matobj.coreferents = list(material.coreferents)
    matobj.components = list(material.components)
    matobj.additional_info = {}
    matobj.extraction_info = extraction_info

    if material.role:
        matobj.additional_info.update({
            'material_role': material.role
        })

    matobj.insert(db)
    return True


def add_property(db, para : orm.PaperTexts, extraction_info : dict,
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

    material = get_material(db, para.id, material_name)
    if material is None:
        log.error("Material {} not found in extracted_materials "
                 "to store properties.", material_name)
        return False

    # check if already exists
    if orm.ExtractedProperties().get_one(db, {
        'material_id': material.id, 'entity_name': prop.entity_name,
        'numeric_value': numeric_value
    }):
        return False

    propobj = orm.ExtractedProperties()
    propobj.material_id = material.id
    propobj.entity_name = prop.entity_name
    propobj.value = prop.property_value
    propobj.coreferents = list(prop.coreferents)
    propobj.numeric_value = numeric_value
    propobj.numeric_error = prop.property_numeric_error
    propobj.value_average = prop.property_value_avg
    propobj.value_descriptor = prop.property_value_descriptor
    propobj.unit = prop.property_unit
    propobj.extraction_info = extraction_info

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

import pylogg
from backend.record_extraction.base_classes import (
    MaterialMention, PropertyValuePair, MaterialAmount
)
from . import orm

log = pylogg.New("persist")


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
        'method_id': method.id,
        'para_id': para_id,
        'entity_name': material_name
    })


def add_material(db, para : orm.PaperTexts, method : orm.ExtractionMethods,
                 material : MaterialMention) -> int:

    assert type(material) == MaterialMention

    entity_name = material.entity_name
    if not entity_name:
        log.warn("Empty material entity name.")
        return None
   
    rowid = orm.ExtractedMaterials().exists(db,
            para_id = para.id, method_id = method.id, entity_name = entity_name)

    if rowid:
        return rowid

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
    return matobj.id


def add_property(db, para : orm.PaperTexts, method : orm.ExtractionMethods,
                 material : MaterialMention, prop : PropertyValuePair,
                 conditions : str = "", details : dict = {}) -> int:
    """ Add extracted properties values to postgres.
        Check uniqueness based on material id and property entity name,
        and numeric value.
        Returns true if the row was added to db.
    """
    assert type(material) == MaterialMention
    assert type(prop) == PropertyValuePair

    material_name = material.entity_name
    if not material_name:
        log.warn("Empty material name.")
        return None

    # Make sure it's a number or ignore.
    numeric_value = prop.property_numeric_value
    try:
        numeric_value = float(numeric_value)
    except:
        log.warn("Invalid numeric value for property: {}", numeric_value)
        return None
    
    matid = orm.ExtractedMaterials().exists(db,
            para_id = para.id, method_id = method.id,
            entity_name = material_name)

    if matid is None:
        log.error("Material {} not found in extracted_materials "
                  "to store properties.", material_name)
        return None

    propid = orm.ExtractedProperties().exists(db,
            method_id = method.id, material_id = matid,
            entity_name = prop.entity_name, numeric_value = numeric_value)
    if propid:
        return propid

    propobj = orm.ExtractedProperties()
    propobj.material_id = matid
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
    return propobj.id


def add_material_property_rel(db, material_id, prop_id, method_id) -> int:
    relid = orm.RelMaterialProperties().exists(
        db, material_id = material_id,
        property_id = prop_id, method_id = method_id
    )

    if relid:
        return relid

    rel = orm.RelMaterialProperties()
    rel.material_id = material_id
    rel.property_id = prop_id
    rel.method_id = method_id

    rel.insert(db)
    return rel.id


def add_material_amount(
        db, paragraph: orm.PaperTexts, method : orm.ExtractionMethods,
        amount: MaterialAmount) -> int:
    """ Add an extracted material amount entry to postgres.
        Check uniqueness based on material id and material entity name.

        Returns true if the row was added to db.
    """
    assert type(amount) == MaterialAmount

    name: str = amount.entity_name
    if not name:
        log.warn("Empty material amount entity name.")
        return None
    
    amtid = orm.ExtractedAmount().exists(db, {
        'method_id': method.id,
        'para_id': paragraph.id,
        'entity_name': name,
    })

    if amtid:
        return amtid

    amtobj = orm.ExtractedAmount()
    amtobj.para_id = paragraph.id
    amtobj.method_id = method.id
    amtobj.entity_name = name
    amtobj.material_amount = amount.material_amount

    amtobj.insert(db)
    return amtid.id


def add_crossref(db, para : orm.PaperTexts, name : str, othername : str,
                 reftype : str) -> int :
    """ Add a cross reference to the database.
        Returns the id of the existing/inserted row.
    """
    refid = orm.ExtractedCrossrefs().exists(db, name=name, reftype=reftype)
    if refid:
        return refid
    
    ref = orm.ExtractedCrossrefs()
    ref.paper_id = para.pid
    ref.para_id = para.id
    ref.name = name
    ref.othername = othername
    ref.reftype = reftype

    ref.insert(db)
    return ref.id

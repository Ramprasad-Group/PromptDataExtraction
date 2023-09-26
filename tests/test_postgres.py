# USAGE: pytest tests/test_pipeline.py -s

import pytest
from backend import postgres

@pytest.fixture
def db():
    return postgres.connect('polylet')

@pytest.fixture
def method(db):
    from backend.postgres import persist
    m = persist.get_method(db, name='test')
    assert m is not None
    return m

@pytest.fixture
def material():
    from backend.record_extraction.base_classes import MaterialMention
    material = MaterialMention()
    material.entity_name = 'test_material'
    material.material_class = 'POLYMER'
    material.role = 'testing'
    return material

@pytest.fixture
def prop():
    from backend.record_extraction.base_classes import PropertyValuePair
    prop = PropertyValuePair()
    prop.entity_name = 'test_property'
    prop.property_value = '300 K'
    prop.property_numeric_error = 1.2
    prop.property_numeric_value = 300
    prop.property_unit = 'K'
    prop.condition_str = 'test_condition'
    return prop

@pytest.fixture
def db_paragraph(db):
    from backend.postgres import orm
    paragraph = orm.PaperTexts().get_one(db)
    assert paragraph is not None
    return paragraph


def test_connection(db):
    assert db is not None


def test_add_material(db, material, db_paragraph, method):
    from backend.postgres import persist, orm

    # try adding new material
    ret = persist.add_material(db, db_paragraph, method, material)
    assert ret == True

    # check if added
    ret = persist.get_material(
        db, db_paragraph.id, material.entity_name, method)
    assert ret is not None
    assert ret.id is not None
    assert type(ret.id) == int
    print("Added materials ID:", ret.id)
    assert ret.entity_name == material.entity_name
    assert ret.para_id == db_paragraph.id

    # check if paragraph id and text matches
    fetch_para : orm.PaperTexts = orm.PaperTexts().get_one(
        db, {'id': ret.para_id})
    assert fetch_para is not None
    assert fetch_para.text == db_paragraph.text

    # The previous things will work via the ORM without commiting first.
    # We can commit here to make sure.
    db.commit()

    # delete the added material
    db.delete(ret)
    db.commit()

    # check if deleted
    ret = persist.get_material(
        db, db_paragraph.id, material.entity_name, method)
    assert ret is None

    db.close()


def test_add_property(db, material, prop, db_paragraph, method):
    from backend.postgres import persist, orm
    
    # we first need to add the material
    persist.add_material(db, db_paragraph, method, material)

    conditions = "condition string"
    details = {'detail': 'test'}

    # try to add the property
    ret = persist.add_property(
        db, db_paragraph, method, material, prop, conditions, details)

    assert ret == True
    db.commit()

    # get the added material
    mat = persist.get_material(
        db, db_paragraph.id, material.entity_name, method)
    assert mat is not None

    # get the added property
    ret : orm.ExtractedProperties = orm.ExtractedProperties().get_one(
        db, {'entity_name': prop.entity_name})
    assert ret is not None
    assert ret.material_id == mat.id
    assert ret.numeric_value == prop.property_numeric_value

    # needs to be removed and commited first due to foreign key.
    db.delete(ret)
    db.commit()

    # next the material
    db.delete(mat)
    db.commit()

    # Check if deleted
    ret : orm.ExtractedProperties = orm.ExtractedProperties().get_one(
        db, {'entity_name': prop.entity_name})
    assert ret is None

    db.close()


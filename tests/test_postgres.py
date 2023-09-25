# USAGE: pytest tests/test_pipeline.py -s

import pytest
from backend import postgres, sett

@pytest.fixture
def db():
    return postgres.connect('testdb')

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

@pytest.fixture
def db_paragraph(db):
    from backend.postgres import orm
    paragraph = orm.PaperTexts().get_one(db)
    assert paragraph is not None
    return paragraph

def test_connection(db):
    assert db is not None


def test_add_material(db, material, db_paragraph):
    from backend.postgres import persist, orm

    # try adding new material
    ret = persist.add_material(db, db_paragraph, {'info': 'test'}, material)
    assert ret == True
    db.commit()

    # check if added
    ret = persist.get_material(db, db_paragraph.id, material.entity_name)
    assert ret is not None
    assert ret.entity_name == material.entity_name
    assert ret.para_id == db_paragraph.id

    # check if paragraph id and text matches
    fetch_para : orm.PaperTexts = orm.PaperTexts().get_one(
        db, {'id': ret.para_id})
    assert fetch_para is not None
    assert fetch_para.text == db_paragraph.text

    # delete the added material
    db.delete(ret)
    db.commit()

    # check if deleted
    ret = persist.get_material(db, db_paragraph.id, material.entity_name)
    assert ret is None

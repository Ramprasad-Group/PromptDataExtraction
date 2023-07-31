# Usage: python -m pytest -v tests/test_database.py

from prompt_extraction.utils import connect_database, connect_remote_database

def test_remote_db():
    db = connect_remote_database()
    assert db is not None 
    collections = ['polymer_DOI_records_dev', 'polymer_DOI_records_prod']
    for coll in collections:
        assert coll in db.list_collection_names()

def test_local_db():
    db = connect_database()
    assert db is not None 
    collections = ['polymer_DOI_records_dev', 'polymer_DOI_records_prod']
    for coll in collections:
        assert coll in db.list_collection_names()

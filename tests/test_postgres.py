from backend import postgres

def test_connection():
    db = postgres.connect()
    assert db is not None

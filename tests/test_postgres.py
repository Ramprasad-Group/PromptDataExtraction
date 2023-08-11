from backend import postgres

def test_connection():
    postgres.load_settings()
    db = postgres.connect()
    assert db is not None

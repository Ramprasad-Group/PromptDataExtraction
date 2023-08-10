from pymongo import MongoClient
import sett

def connect():
    client = MongoClient(
        host=sett.MongoDb.host,
        port=sett.MongoDb.port,
        username=sett.MongoDb.username,
        password=sett.MongoDb.password,
        authSource=sett.MongoDb.authSource,
    )
    db = client[sett.MongoDb.dbname]
    return db

import sett
from backend import postgres
from backend.postgres.orm import (
    TableMeta, PaperData, Papers, PaperSections, Polymers
)

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

meta = TableMeta(Polymers())
meta.description = "Polymer name list with name normalization"
meta.codeversion = None
meta.tag = None

meta.insert(db)
db.commit()

print("Insert OK:", meta.table, meta.description)

import re
import json

import sett
import pylogg
from tqdm import tqdm

from backend import postgres
from backend.postgres.orm import Polymers
from backend.utils.frame import Frame

pylogg.setMaxLength(1000)
sett.load_settings()

postgres.load_settings()
db = postgres.connect()

def fix_smiles(string : str) -> str:
    string = re.sub(r'%\d\d', r'', string)
    if string.startswith("{") and " " in string:
        string = ";".join([p.strip(",{}") for p in string.split()])
    return string

with open(sett.Dataset.polymer_nen_json) as fp:
    nen = json.load(fp)

for name, val in nen.items():
    print(name)
    norm = Polymers()
    norm.name = name
    norm.is_norm = True
    norm.norm_id = None

    norm.is_polymer = not val['not_polymer']
    norm.norm_name = name
    norm.iupac_name = val['IUPAC_structure']

    norm.smiles = fix_smiles(val['smile_string'])
    norm.is_copolymer = bool(val['copolymer'])
    norm.is_composite = bool(val['composite'])
    norm.is_blend = bool(val['polymer_blend'])
    norm.comments = {
        k.title().strip() : v
        for k, v in val.items() if 'omments' in k and v
    }
    norm.details = {}

    print(norm.__dict__)
    norm.insert(db)
    db.commit()

    nid = Polymers().get_one(db, {'name': name}).id

    for coref in val['coreferents']:
        if coref == name:
            continue
        polycoref = Polymers()
        polycoref.name = coref
        polycoref.is_norm = False
        polycoref.norm_id = nid
        polycoref.norm_name = norm.name
        polycoref.is_polymer = norm.is_polymer
        polycoref.iupac_name = val['IUPAC_structure']
        polycoref.smiles = norm.smiles
        polycoref.is_copolymer = bool(val['copolymer'])
        polycoref.is_composite = bool(val['composite'])
        polycoref.is_blend = bool(val['polymer_blend'])
        polycoref.comments = norm.comments
        polycoref.details = norm.details
        print("Coref:", polycoref.__dict__)
        polycoref.insert(db)

    db.commit()

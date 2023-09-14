import re
import json

import pylogg as log
from tqdm import tqdm

from backend import postgres, sett
from backend.postgres.orm import PropertyMetadata
from backend.utils.frame import Frame

log.setMaxLength(1000)
sett.load_settings()

postgres.load_settings()
db = postgres.connect()

with open(sett.DataFiles.properties_json) as fp:
    metadata = json.load(fp)

for prop, value in metadata.items():
    print(prop)

    meta = PropertyMetadata()
    meta.name = prop
    meta.other_names = list(value.get('property_list', []))
    meta.units = list(value.get('unit_list', []))
    meta.scale = 'log' if value.get('log_scale', False) else 'normal'
    meta.short_name = value.get('short_name')
    limits = value.get('axes_lim', [None, None])
    meta.lower_limit = limits[0]
    meta.upper_limit = limits[1]
    
    meta.insert(db)
    log.info("Added property info: {}", prop)

db.commit()


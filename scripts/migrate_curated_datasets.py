import pylogg as log
from tqdm import tqdm

from backend import postgres, sett
from backend.postgres.orm import CuratedData
from backend.data.dataset_pranav import GroundDataset

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

t1 = log.info("Loading ground truth dataset.")
ds = GroundDataset()

property_name = 'bandgap'

gnd, nlp = ds.create_dataset(mode=property_name)
t1.done("Loaded dataset.")


for doi, value in tqdm(gnd.items()):
    abstract = [item['abstract'] for item in value if item['abstract'] != ''][0]

    for record in value:
        cure = CuratedData()
        cure.doi = doi
        cure.text = abstract
        cure.text_type = 'abstract'
        cure.material = record.get('material')
        cure.material_coreferents = list(record.get('material_coreferents'))
        cure.property_name = property_name
        cure.property_value = record.get('property_value')
        cure.insert(db)

    # log.info("Added property info: {}", doi)

db.commit()
log.close()

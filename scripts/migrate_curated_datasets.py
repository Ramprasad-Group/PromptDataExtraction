import os
import pylogg as log
from tqdm import tqdm

from backend import postgres, sett
from backend.postgres.orm import CuratedData, Papers, PaperTexts
from backend.data.dataset_pranav import GroundDataset
from backend.text.normalize import normText

sett.load_settings()
os.makedirs(sett.Run.directory, exist_ok=True)
log.init(sett.Run.logLevel, sett.Run.directory)

postgres.load_settings()
db = postgres.connect()

t1 = log.info("Loading ground truth dataset.")
ds = GroundDataset()

property_name = 'Tg'

gnd, nlp = ds.create_dataset(mode=property_name)
t1.done("Loaded dataset.")


for doi, value in tqdm(gnd.items()):
    abstract = [item['abstract'] for item in value if item['abstract'] != ''][0]
    abstract = normText(abstract)

    paper : Papers = Papers().get_one(db, {'doi': doi})
    if paper is None:
        log.error("No such paper in DB: {}", doi)
        continue

    # Add the text to paper texts.
    para : PaperTexts = PaperTexts().get_one(db, {
        'pid': paper.id, 'text': abstract})
    
    if para is None:
        log.trace("Abstract not found in paragraphs: {}", doi)

        # Add the abstract to paper text
        para = PaperTexts()
        para.doi = doi
        para.pid = paper.id
        para.doctype = paper.doctype
        para.section = "abstract"
        # para.text = abstract
        para.text = abstract
        para.directory = paper.directory

        para.insert(db)
        db.commit()
        para : PaperTexts = PaperTexts().get_one(db, {
            'pid': paper.id, 'text': abstract})

    # Add the curated records and link to paper texts.
    for record in value:
        cure = CuratedData()
        cure.para_id = para.id
        cure.doi = doi
        cure.material = record.get('material')
        cure.material_coreferents = list(record.get('material_coreferents'))
        cure.property_name = property_name
        cure.property_value = record.get('property_value')
        cure.insert(db)

    log.trace("Added property info: {}", doi)

db.commit()
log.close()

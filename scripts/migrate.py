import sett
import pylogg
from tqdm import tqdm
from backend.data import mongodb
from backend import postgres
from backend.postgres.orm import Papers, PaperSections

pylogg.setMaxLength(1000)
sett.load_settings()

postgres.load_settings()
db = postgres.connect()

# def fix_doi(doi : str):
#     # Fix the dois
#     doi = doi.replace("@", "/").rstrip('.html')
#     doi = doi.rstrip(".xml")
#     return doi

# paper = Paper()
# i = 0
# for p in tqdm(paper.get_all(db)):
#     if "@" in p.doi:
#         p.doi = fix_doi(p.doi)
#     if 'aip' in p.publisher:
#         p.publisher = 'AIP Publishing'

#     i += 1
#     if i >= 1000:
#         db.commit()
#         i = 0

# if i > 0:
#     db.commit()

# Load full text data from mongodb and migrate to postgres
mongo = mongodb.connect()
coll = mongo[sett.PEFullText.mongodb_collection]

query = {'full_text': {'$exists': True}}

cursor = coll.find(query, no_cursor_timeout=True)
num_docs = coll.count_documents(query)
print("Docs with full_text:", num_docs)

# print(coll.distinct('publisher'))

def add_section(sec, doi, form, pid):
    try:
        stype = sec['type']
        sname = sec['name']
        stext = sec['content']
    except:
        return False

    sname = sname.lower().rstrip(".:")

    if type(stext) == list and len(stext) > 1:
        for text in stext:
            if type(text) == dict:
                add_section(text, doi, form, pid)
            if type(text) == str:
                text = {
                    'type': stype,
                    'name': sname,
                    'content': text,
                }
                add_section(text, doi, form, pid)
        return True

    if type(stext) == list and len(stext) == 1:
        stext = stext[0]

    if type(stext) == dict:
        return add_section(stext, doi, form, pid)
    
    if type(stext) != str:
        return False

    if len(stext) < 3:
        return False

    stype = stype.replace('section', '').strip('_').lower()

    # print(sname, "::", stext)

    if PaperSections().get_one(db, {
        'doi': doi, 'type': stype, 'name': sname}):
        return False

    section = PaperSections(
        doi = doi,
        format = form,
        type = stype,
        name = sname,
        text = stext,
        pid = pid,
    )

    section.insert(db)
    return True


i = 0
n = 0
with coll.find(query, no_cursor_timeout=True) as cursor:
    for doc in tqdm(cursor, total=num_docs):
        doi = doc.get('DOI')
        abstract = doc.get('abstract')
        fulltext = doc.get('full_text')

        paper = Papers().get_one(db, {'doi': doi})
        if not paper:
            print("Paper Not Found:", doi)
            continue

        pub = doc.get('publisher')
        form = 'html'
        if 'ACS' in pub: form = 'xml'
        elif 'Elsevier' in pub: form = 'xml'

        for sec in fulltext:
            if type(sec) == dict:
                if not add_section(sec, doi, form, paper.id):
                    continue

                n += 1
                i += 1
                if i >= 10000:
                    print("Total added:", n)
                    # exit(0)
                    db.commit()
                    i = 0

if i > 0:
    db.commit()
print("Total added:", n)

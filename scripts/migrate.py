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
print("Docs with full_text:", num_docs, flush=True)


def para_generator(node, para_name, para_type):
    for para in node:
        if type(para) == dict:
            yield from para_generator(
                para['content'], para_name=para['name'],
                para_type=para.get('type'))
        elif type(para) == str:
            yield para, para_name, para_type
        else:
            raise ValueError


def add_para(doi, form, pid, stext, sname, stype):
    if len(stext) < 3:
        return False

    stype = stype.replace('section', '').strip('_').lower()
    sname = sname.lower().rstrip(".:")

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
j = 0
n = 0
para = 0

with coll.find(query, no_cursor_timeout=True) as cursor:
    # for doc in tqdm(cursor, total=num_docs):
    for doc in cursor:
        j += 1
        doi = doc.get('DOI')
        fulltext = doc.get('full_text')

        paper = Papers().get_one(db, {'doi': doi})
        if not paper:
            print("Paper Not Found:", doi)
            continue

        pub = doc.get('publisher')
        form = 'html'
        if 'ACS' in pub: form = 'xml'
        elif 'Elsevier' in pub: form = 'xml'

        for sec in para_generator(fulltext, 'main', 'body'):
            stext, sname, stype = sec
            para += 1

            if not add_para(doi, form, paper.id, stext, sname, stype):
                continue

            n += 1
            i += 1
            if i >= 10000:
                # exit(0)
                db.commit()
                i = 0

        if not j % 10000:
            print("Total para added:", n, "out of:", para)
            print("Document processed:", j, "out of:", num_docs, flush=True)


if i > 0:
    db.commit()

print("Total para added:", n, "out of:", para)
print("Document processed:", j, "out of:", num_docs)

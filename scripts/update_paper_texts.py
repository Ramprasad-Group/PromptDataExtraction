""" Migrate abstracts to paper_texts table """

import pylogg as log

from backend import postgres, sett
from backend.postgres.orm import Papers, PaperTexts

def add_to_postgres(paper : Papers):
    """ Add a paragraph text to postgres if it already does not
        exist in the database.
    """

    paragraph = PaperTexts().get_one(db, {'doi': paper.doi, 'text': paper.abstract})
    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {paper.abstract}. Skipped.")
        return False
    
    paragraph = PaperTexts()
    paragraph.pid = paper.id
    paragraph.directory = paper.directory
    paragraph.doi = paper.doi
    paragraph.doctype = paper.doctype
    paragraph.section = 'abstract'
    paragraph.tag = None
    paragraph.text = paper.abstract
    paragraph.insert(db)

    log.trace(f"Added to PostGres: {paper.abstract}")

    return True

sett.load_settings()
postgres.load_settings()
db = postgres.connect()


query = """
SELECT p.id FROM papers p JOIN filtered_papers fp ON fp.doi = p.doi;
"""

t2 = log.info("Querying list of filtered polymer DOIs.")
records = postgres.raw_sql(query)
t2.done("Found {} DOIs.", len(records))

n = 0
pg = 0

for row in records:
    n += 1

    paper = Papers().get_one(db, {'id': row.id})
    if paper and add_to_postgres(paper):
        pg += 1

    if not n % 50:
        log.info("Processed {}, added {}", n, pg)
        db.commit()

    if sett.Run.debugCount > 0 and n >= sett.Run.debugCount:
        log.info("Processed {}, added {} paragraphs", n, pg)
        break


db.commit()

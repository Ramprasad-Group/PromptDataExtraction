#!/usr/bin/env python
"""
Walk a corpus directory and parse the text section of the papers.
Validate, normalize and add to database.

"""

import os
import sys
import sett
import pylogg as log

from backend.data import mongodb

from backend import postgres
from backend.postgres.orm import Papers, PaperTexts

from backend.utils.frame import Frame
from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

mongo = mongodb.connect()
collection = mongo[sett.FullTextParse.mongodb_collection]


def add_to_mongodb(doi : str, publisher : str, doctype : str,
                   para : ParagraphParser):
    """ Add a paragraph text to mongodb if it already does not
        exist in the database.
    """

    itm = collection.find_one({'DOI': doi})
    if itm is None:
        log.error(f"{doi} not found in MongoDB.")
        return False
    
    fulltext = itm.get('full_text')
    newsection = {
        "type": 'paragraph',
        "pub": publisher,
        "format": doctype,
        "name": "main",
        "content": [para.text.strip()]
    }

    # do not add abstract
    abstract = itm.get('abstract', '')
    if type(abstract) == list and len(abstract) > 0:
        abstract = abstract[0]
    else:
        abstract = ''
    if para.text.strip() == abstract.strip():
        return False

    if fulltext is not None:
        for section in fulltext:
            if 'content' in section:
                if para.text.strip() in section['content']:
                    log.trace(f"Paragraph in MongoDB: {para.text}. Skipped.")
                    return False
        fulltext.append(newsection)
    else:
        fulltext = [newsection]

    record_id = itm.get('_id')
    collection.update_one({"_id": record_id}, {
            "$set": {
                "full_text": fulltext
            }
        }
    )

    log.trace(f"Add to MongoDB: {para.text}")
    return True


def add_to_postgres(paper : Papers, publisher : str, doctype : str,
                    para : ParagraphParser):
    """ Add a paragraph text to postgres if it already does not
        exist in the database.
    """

    paragraph = PaperTexts().get_one(db, {'doi': paper.doi, 'text': para.text})
    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {para.text}. Skipped.")
        return False
    
    paragraph = PaperTexts()
    paragraph.pid = paper.id
    paragraph.pub = publisher
    paragraph.doi = paper.doi
    paragraph.doctype = doctype
    paragraph.section = None
    paragraph.tag = None
    paragraph.text = para.text
    paragraph.insert(db)

    log.trace(f"Added to PostGres: {para.text}")

    return True


def parse_file(filepath, root = "") -> DocumentParser | None:    
    # Keep count of added items for statistics
    pg =  0
    mn = 0

    filename = os.path.basename(filepath)
    formatted_name = filepath.replace(root, "")

    doi = filename2doi(filename)
    publisher = filepath.split("/")[-2]

    doc = PaperParser(publisher, filepath)
    if doc is None:
        log.warn(f"Ignore: {formatted_name} (Parser not found)")
        return None, pg, mn

    try:
        doc.parse(parse_tables=False)
        log.trace("Parsed document: {}", filepath)
        log.trace("Found {} paragraphs", len(doc.paragraphs))
    except Exception as err:
        log.error("Failed to parse: {} ({})", formatted_name, err)
        return None, pg, mn

    if sett.FullTextParse.debug:
        for para in doc.paragraphs:
            print("\t", "-" * 50)
            print("\t", para.text, flush=True)

    if sett.FullTextParse.add2mongo:
        for para in doc.paragraphs:
            if add_to_mongodb(doi, publisher, doc.doctype, para):
                mn += 1

    if sett.FullTextParse.add2postgres:
        # get the foreign key
        paper = Papers().get_one(db, {'doi': doi})

        for para in doc.paragraphs:
            if paper is None:
                log.warn(f"{doi} not found in postgres.")
                break
            elif add_to_postgres(paper, publisher, doc.doctype, para):
                pg += 1

        db.commit()

    return doc, pg, mn


def walk_directory():
    """ Recursively walk a directory containing literature files.
        Create a CSV list by parsing meta information.
    """
    outcsv = sett.FullTextParse.runName + "/parse_papers_info.csv"
    directory = sett.FullTextParse.paper_corpus_root_dir

    # How many files to parse
    max_files = sett.FullTextParse.debugCount \
        if sett.FullTextParse.debug else -1

    log.info("Walking directory: %s" %directory)
    df = Frame()

    # Recursively crawl the corpus ...
    for root, subdirs, files in os.walk(directory):
        n = 1
        total_pg = 0
        total_mn = 0
        log.trace("Entering: %s" %root)

        for filename in files:
            abs_path = os.path.join(root, filename)
            doc, pg, mn = parse_file(abs_path, directory)

            if doc is None:
                continue

            df.add(filename=filename, filepath=doc.docpath, ftype=doc.doctype,
                    publisher=doc.publisher, npara=len(doc.paragraphs),
                    postgres_added=pg, mongodb_added=mn)

            # Not more than max_files per directory
            # Use -1 for no limit.
            n += 1
            total_pg += pg
            total_mn += mn

            if (n-1) % 50 == 0:
                log.info("Processed {} papers. Added {} paragraphs to Postgres."
                         " Added {} paragraphs to MongoDB",
                         n-1, total_pg, total_mn)

            if max_files > 0 and n > max_files:
                log.note("Processed maximum {} papers.", n-1)
                log.info("Added {} paragraphs to Postgres, "
                         "{} paragraphs to MongoDB.", total_pg, total_mn)
                break

    # save the file list
    df.save(outcsv)


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


def log_run_info():
    """
        Log run information for reference purposes.
        Returns a log Timer.
    """
    t1 = log.note("FullTextParse Run: {}", sett.FullTextParse.runName)
    log.info("CWD: {}", os.getcwd())
    log.info("Host: {}", os.uname())

    if sett.FullTextParse.debug:
        log.note("Debug run. Will parse maximum {} files.",
                 sett.FullTextParse.debugCount)
    else:
        log.note("Production run. Will parse all files in {}",
                 sett.FullTextParse.paper_corpus_root_dir)

    log.info("Using loglevel = {}", sett.FullTextParse.loglevel)

    if not sett.FullTextParse.add2mongo:
        log.warn("Will not be adding to mongodb.")
    else:
        log.note("Will be adding to mongo collection: {}",
                 sett.FullTextParse.mongodb_collection)

    if not sett.FullTextParse.add2postgres:
        log.warn("Will not be adding to postgres.")
    else:
        log.note("Will be adding to postgres table: paper_texts")

    return t1


if __name__ == '__main__':
    
    os.makedirs(sett.FullTextParse.runName, exist_ok=True)
    log.setFile(open(sett.FullTextParse.runName+"/parse_papers.log", "w+"))
    log.setLevel(sett.FullTextParse.loglevel)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)

    t1 = log_run_info()

    if len(sys.argv) > 1:
        parse_file(sys.argv[1])
    else:
        walk_directory()

    t1.done("All Done.")
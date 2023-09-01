#!/usr/bin/env python
"""
Walk a corpus directory and parse the text section of the papers.
Validate, normalize and add to database.

"""

import os
import sys
import sett
import pylogg as log
from tqdm import tqdm

from backend.data import mongodb

from backend import postgres
from backend.postgres.orm import Papers, PaperSections

from backend.utils.frame import Frame
from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

mongo = mongodb.connect()
collection = mongo[sett.FullTextParse.mongodb_collection]


def add_to_mongodb(doi : str, para : ParagraphParser):
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
        "name": "main",
        "content": [para.text.strip()]
    }

    # do not add abstract
    abstract = itm.get('abstract', '')
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


def add_to_postgres(doi : str, doctype : str, para : ParagraphParser):
    """ Add a paragraph text to postgres if it already does not
        exist in the database.
    """
    paragraph = PaperSections().get_one(db, {'doi': doi, 'text': para.text})
    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {para.text}. Skipped.")
        return False
    
    # get the foreign key
    paper = Papers().get_one(db, {'doi': doi})
    if paper is None:
        log.error(f"{doi} not found in postgres.")
        return False

    paragraph = PaperSections()
    paragraph.pid = paper.id
    paragraph.doi = doi
    paragraph.name = 'main'
    paragraph.format = doctype
    paragraph.text = para.text
    paragraph.type = 'body'
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
        log.trace("Parsed document: {}", formatted_name)
    except Exception as err:
        log.error("Failed to parse: {} ({})", formatted_name, err)
        return None, pg, mn

    # Print the paragraphs
    for para in doc.paragraphs:
        # print("\t", "-" * 50)
        # print("\t", para.text)
        if add_to_postgres(doi, doc.doctype, para):
            pg += 1
        if add_to_mongodb(doi, para):
            mn += 1

    return doc, pg, mn


def walk_directory():
    """ Recursively walk a directory containing literature files.
        Create a CSV list by parsing meta information.
    """
    outcsv = 'parse_papers_info.csv'
    directory = sett.FullTextParse.paper_corpus_root_dir

    max_files = 100 if sett.Run.debug else -1

    log.trace("Walking directory: %s" %directory)
    df = Frame()

    # Recursively crawl the corpus ...
    for root, subdirs, files in os.walk(directory):
        n = 1
        log.trace("Entering: %s" %root.replace(directory, "./"))

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

            if (n-1) % 50 == 0:
                db.commit()
                log.info("Processed {} papers.", n-1)

            if max_files > 0 and n > max_files:
                log.note("Processed maximum {} papers.", n-1)
                break

    # save the file list
    df.save(outcsv)


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


if __name__ == '__main__':
    log.setLevel(log.DEBUG)

    if len(sys.argv) > 1:
        parse_file(sys.argv[1])
        db.commit()

    else:
        walk_directory()

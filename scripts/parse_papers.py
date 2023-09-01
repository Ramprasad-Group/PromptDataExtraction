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

from backend import postgres
from backend.data import mongodb

from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser
from backend.utils.frame import Frame
from backend.postgres.orm import Papers, PaperSections


sett.load_settings()
postgres.load_settings()
db = postgres.connect()

# mongo = mongodb.connect()
# coll = mongo[sett.PEFullText.mongodb_collection]


def add_to_mongodb(doi : str, doc : DocumentParser):
    """ Add the paragraphs of a document to mongodb if they already do not
        exist in the database.
    """
    pass


def add_to_postgres(doi : str, doctype : str, para : ParagraphParser):
    paragraph = PaperSections().get_one(db, {'doi': doi, 'text': para.text})
    if paragraph is not None:
        log.trace(f"{doi}: In PostGres: {para.text}. Skipped.")
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
    db.commit()
    return True


def parse_file(filepath, root = "") -> DocumentParser | None:
    filename = os.path.basename(filepath)
    formatted_name = filepath.replace(root, "")

    doi = filename2doi(filename)
    print('DOI:', doi, filename)

    # if not sett.Run.db_update:
    #     # If update is not requested,
    #     # check if the paper already exists in db and skip.
    #     paper = PaperTexts().get_one(db, {'doi': doi})
    #     if paper is not None:
    #         log.trace("In DB: %s. Skipped." %filename)
    #         return None

    ftype = 'xml' if filename.endswith('xml') else 'html'
    publisher = filepath.split("/")[-2]

    doc = PaperParser(publisher, filepath)
    if doc is None:
        log.warn(f"Ignore: {formatted_name} (Parser not found)")
        return None

    try:
        doc.parse(parse_tables=False)
        log.trace("Parsed document: {}", formatted_name)
    except Exception as err:
        log.error("Failed to parse: {} ({})", formatted_name, err)
        return None

    # Print the paragraphs
    for para in doc.paragraphs:
        print("\t", "-" * 50)
        print("\t", para.text)
        add_to_postgres(doi, doc.doctype, para)

    return doc


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
            doc = parse_file(abs_path, directory)

            if doc is None:
                continue

            df.add(filename=filename, filepath=doc.docpath, ftype=doc.doctype,
                    publisher=doc.publisher, npara=len(doc.paragraphs))

            #@Todo: save to db

            # Not more than max_files per directory
            # Use -1 for no limit.
            n += 1

            if (n-1) % 50 == 0:
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
    if len(sys.argv) > 1:
        parse_file(sys.argv[1])
    else:
        walk_directory()

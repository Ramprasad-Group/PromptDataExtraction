#!/usr/bin/env python
"""
Walk a corpus directory and parse the text section of the papers.
Validate, normalize and add to database.

"""

import os
import sys
import pylogg as log

from backend import postgres, sett
from backend.postgres.orm import Papers, PaperTexts

from backend.utils.frame import Frame
from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

sett.load_settings()
postgres.load_settings()
db = postgres.connect()


def add_to_postgres(paper : Papers, directory : str, doctype : str,
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
    paragraph.directory = directory
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
    directory = filepath.split("/")[-2]

    doc = PaperParser(directory, filepath)
    if doc is None:
        log.error(f"Ignore: {formatted_name} (Parser not found)")
        return None, pg

    try:
        doc.parse(parse_tables=False)
        log.trace("Parsed document: {}", filepath)
        log.trace("Found {} paragraphs", len(doc.paragraphs))
    except Exception as err:
        log.error("Failed to parse: {} ({})", formatted_name, err)
        return None, pg

    if sett.Run.debugCount > 0:
        for para in doc.paragraphs:
            print("\t", "-" * 50)
            print("\t", para.text, flush=True)

    if sett.FullTextParse.add2postgres:
        # get the foreign key
        paper = Papers().get_one(db, {'doi': doi})

        for para in doc.paragraphs:
            if paper is None:
                log.warn(f"{doi} not found in postgres.")
                break
            elif add_to_postgres(paper, directory, doc.doctype, para):
                pg += 1

        db.commit()

    return doc, pg


def parse_polymer_papers(root : str, directory : str = 'acs'):
    # get the list of dois for specific publisher that were not found in
    # paper_texts
    query = """
    SELECT * FROM (
	    SELECT p.doi, p.doctype FROM filtered_papers fp
        JOIN papers p ON p.doi = fp.doi WHERE p.directory = :dirname
    ) AS poly WHERE poly.doi NOT IN (
	    SELECT DISTINCT(pt.doi) FROM paper_texts pt
        WHERE pt.directory = :dirname
    );
    """

    t2 = log.info("Querying list of non-parsed DOIs.")
    records = postgres.raw_sql(query, {'dirname': directory})
    t2.done("Found {} DOIs not parsed.", len(records))

    n = 0
    pg = 0
    total_pg = 0

    for row in records:
        doi = row.doi
        doctype = row.doctype
        filename = doi2filename(doi, doctype)
        abs_path = os.path.join(root, directory, filename)
        if not os.path.isfile(abs_path):
            log.error("File not found: {}", abs_path)

        doc, pg = parse_file(abs_path, directory)
        if doc is None:
            continue

        n += 1
        total_pg += pg

        if (n-1) % 50 == 0:
            log.info("Processed {} papers. Added {} paragraphs to Postgres.",
                     n-1, total_pg)

        # Not more than debugCount per run
        # Use -1 for no limit.
        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            log.note("Processed maximum {} papers.", n-1)
            log.info("Added {} paragraphs to Postgres, ", total_pg)
            break

    # get file name for the doi

    # parse and store the file




def walk_directory():
    """ Recursively walk a directory containing literature files.
        Create a CSV list by parsing meta information.
    """
    outcsv = sett.Run.directory + "/parse_papers_info.csv"
    directory = sett.FullTextParse.paper_corpus_root_dir

    log.info("Walking directory: %s" %directory)
    df = Frame()

    # Recursively crawl the corpus ...
    for root, subdirs, files in os.walk(directory):
        n = 1
        total_pg = 0
        log.trace("Entering: %s" %root)

        for filename in files:
            abs_path = os.path.join(root, filename)
            doc, pg = parse_file(abs_path, directory)

            if doc is None:
                continue

            df.add(filename=filename, filepath=doc.docpath, ftype=doc.doctype,
                    publisher=doc.publisher, npara=len(doc.paragraphs),
                    postgres_added=pg)

            # Not more than debugCount per directory
            # Use -1 for no limit.
            n += 1
            total_pg += pg

            if (n-1) % 50 == 0:
                log.info("Processed {} papers. Added {} paragraphs to DB.",
                         n-1, total_pg)

            if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
                log.note("Processed maximum {} papers.", n-1)
                log.info("Added {} paragraphs to Postgres, ", total_pg)
                break

    # save the file list
    df.save(outcsv)


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi

def doi2filename(doi : str, doctype : str):
    filename = doi.replace("/", "@")
    filename = filename + "." + doctype
    return filename


def log_run_info():
    """
        Log run information for reference purposes.
        Returns a log Timer.
    """
    t1 = log.note("FullTextParse: {}", sett.Run.directory)
    log.info("CWD: {}", os.getcwd())
    log.info("Host: {}", os.uname())

    if sett.Run.debugCount > 0:
        log.note("Debug run. Will parse maximum {} files.",
                 sett.Run.debugCount)
    else:
        log.note("Production run. Will parse all files in {}",
                 sett.FullTextParse.paper_corpus_root_dir)

    log.info("Using loglevel = {}", sett.Run.logLevel)

    if not sett.FullTextParse.add2postgres:
        log.warn("Will not be adding to postgres.")
    else:
        log.note("Will be adding to {}.paper_texts",
                 sett.PostGres.db_name)

    return t1


if __name__ == '__main__':
    
    os.makedirs(sett.Run.directory, exist_ok=True)
    log.setFile(open(sett.Run.directory+"/parse_papers.log", "w+"))
    log.setLevel(sett.Run.logLevel)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)

    t1 = log_run_info()

    if len(sys.argv) > 1:
        parse_file(sys.argv[1])
    else:
        # walk_directory()
        parse_polymer_papers(sett.FullTextParse.paper_corpus_root_dir, 'acs')

    t1.done("All Done.")

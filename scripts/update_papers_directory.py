#!/usr/bin/env python
"""
Walk a corpus directory and parse the text section of the papers.
Validate, normalize and add to database.

"""

import os
import sett
import pylogg as log

from backend import postgres
from backend.postgres.orm import Papers

sett.load_settings()
postgres.load_settings()
db = postgres.connect()

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

    # Recursively crawl the corpus ...
    for root, subdirs, files in os.walk(directory):
        n = 1
        total_pg = 0
        log.trace("Entering: %s" %root)

        for filename in files:
            abs_path = os.path.join(root, filename)
            doi = filename2doi(filename)

            paper = Papers().get_one(db, {'doi': doi})
            if paper is None:
                log.error("Paper {} not in database.", abs_path)
                continue
            paper = Papers()
            paper.directory = abs_path.split("/")[-2]

            log.trace("Paper: {}, directory: {}", doi, paper.directory)

            # Not more than max_files per directory
            # Use -1 for no limit.
            n += 1
            total_pg += 1

            if (n-1) % 50 == 0:
                log.info("Processed {} papers. Added {} paragraphs to Postgres.",
                         n-1, total_pg)

            if max_files > 0 and n > max_files:
                log.note("Processed maximum {} papers.", n-1)
                log.info("Added {} paragraphs to Postgres", total_pg)
                break


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


if __name__ == '__main__':
    os.makedirs(sett.FullTextParse.runName, exist_ok=True)

    t1 = log.init(
        log_level=sett.FullTextParse.loglevel,
        output_directory=sett.FullTextParse.runName)

    walk_directory()

    t1.done("All Done.")
    log.close()

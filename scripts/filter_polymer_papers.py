#!/usr/bin/env python
"""
Go through the papers from the database. Identify the polymer papers
using title and abstracts.

"""

import os
import sett
import pylogg as log

from backend import postgres
from backend.postgres.orm import Papers, FilteredPapers

sett.load_settings()
postgres.load_settings()
db = postgres.connect()


def add_to_postgres(doi : str, filter_name : str, filter_desc : str):
    """ Add a paper to the list of a specific filter.
        Ignore if exists in the database.
    """
    paper = FilteredPapers().get_one(db, {'doi': doi, 'filter_name': filter_name})
    if paper is not None:
        log.trace(f"DOI {doi} in {filter_name}. Skipped.")
        return False

    paper = FilteredPapers()
    paper.doi = doi
    paper.filter_name = filter_name
    paper.filter_desc = filter_desc

    paper.insert(db)
    log.trace(f"Added to {filter_name}: {doi}")
    return True


def filename2doi(doi : str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


def find_papers(debugCount = 100):
    """ Filter all polymer papers and add to postgres.
        If debugCount > 0, process only that many papers.
    """

    name = "polymer_papers"
    desc = "Poly in title or abstract"

    log.info("Finding papers for filter: {} ({})", name, desc)

    n = 0
    found = 0
    pg_added = 0

    for paper in next(Papers().iter(db, size=10)):
        n += 1

        if not paper.title and not paper.abstract:
            log.warn(f"No title or abstract: {paper.doi}")
            continue

        filters = [
            'poly' in paper.title.lower(),
            'poly' in paper.abstract.lower(),
        ]

        if any(filters):
            log.trace(f"Found paper for {name}: {paper.doi} ({paper.title})")
            found += 1

            if add_to_postgres(paper.doi, name, desc):
                pg_added += 1

        if not (n % 100):
            db.commit()
            log.info(f"Processed {n} papers. "
                     f"Filter matched {found}. "
                     f"Added to PostGres {pg_added}.")

        if debugCount > 0 and n >= debugCount:
            log.note(f"Processed maximum {n} papers. "
                     f"Filter matched {found}. "
                     f"Added to PostGres {pg_added}.")
            break


def init_logger(run_name, log_level = 8):
    """
        Log run information for reference purposes.
        Returns a log Timer.
    """
    import sys, os
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    log_file = open(os.path.join(run_name, f"{script_name}.log"), "w+")

    print("Logging to file:", log_file.name)

    log.setLevel(log_level)
    log.setFile(log_file)
    log.setFileTimes(show=True)
    log.setConsoleTimes(show=True)

    t1 = log.info(f"Polymer Filter Run: {run_name}")
    log.info("CWD: {}", os.getcwd())
    log.info("Host: {}", os.uname())
    log.info("Using loglevel = {}", log_level)

    return t1


if __name__ == '__main__':
    runName = "runs/filters/polymer_papers"
    os.makedirs(runName, exist_ok=True)
    t1 = init_logger(runName, log.INFO)

    find_papers(debugCount = 0)

    t1.done("All Done.")

#!/usr/bin/env python
"""
Walk a corpus directory and parse the text section of the papers.
Validate, normalize and add to database.

"""

import os
import sett
import pylogg as log
from tqdm import tqdm

from backend import postgres
from backend.parser import PaperParser
from backend.utils.frame import Frame
from backend.postgres.orm import Papers, PaperTexts


sett.load_settings()
postgres.load_settings()
db = postgres.connect()


def walk_directory():
    """ Recursively walk a directory containing literature files.
        Create a CSV list by parsing meta information.
    """
    outcsv = 'parse_papers_info.csv'
    directory = sett.Dataset.paper_corpus_root_dir

    max_files = 100 if sett.Run.debug else -1

    log.trace("Walking directory: %s" %directory)
    df = Frame()

    # Recursively crawl the corpus ...
    for root, subdirs, files in os.walk(directory):
        n = 1
        log.trace("Entering: %s" %root.replace(directory, "./"))

        for filename in files:
            paper = None

            doi = filename2doi(filename)

            if not sett.Run.db_update:
                # If update is not requested,
                # check if the paper already exists in db and skip.
                paper = PaperTexts().get({'doi': doi})
                if paper is not None:
                    log.trace("In DB: %s. Skipped." %filename)
                    continue

            abs_path = os.path.join(root, filename)
            file_path = abs_path.replace(directory, "")
            ftype = 'xml' if filename.endswith('xml') else 'html'
            publisher = abs_path.split("/")[-2]

            doc = PaperParser(publisher, abs_path)
            if doc is None:
                log.warn(f"Ignore: {file_path} (Parser not found)")
                continue

            try:
                doc.parse()
                log.trace("Parsed document: {}", file_path)
            except Exception as err:
                log.error("Failed to parse: {} ({})", file_path, err)
                continue

            df.add(filename=filename, filepath=file_path, ftype=ftype,
                   publisher=publisher, npara=len(doc.sections.keys()))

            # Print the sections
            for k, v in doc.sections.items():
                print(k, "============================")
                print(v)

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

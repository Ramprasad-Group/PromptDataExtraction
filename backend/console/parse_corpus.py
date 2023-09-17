import os
import pylogg
from datetime import datetime
from argparse import ArgumentParser, _SubParsersAction

from backend import postgres, sett
from backend.postgres.orm import PaperCorpus

ScriptName = 'parse-corpus'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Crawl the list of files from a directory in the corpus.')
    parser.add_argument(
        'directory',
        help="Path to directory in the corpus.")


def _add_to_postgres(db, abspath : str, rootdir : str = ''):
    """ Add a paragraph text to postgres if it already does not
        exist in the database.
    """

    filename = os.path.basename(abspath)
    doistr = filename2doi(filename)

    paperfile = PaperCorpus().get_one(db, {'doi': doistr})
    if paperfile is not None:
        log.trace(f"Paper file in PostGres: {doistr}. Skipped.")
        return False

    # Add the file to database.
    doctype = os.path.splitext(abspath)[1][1:]
    directory = os.path.basename(os.path.dirname(abspath))
    relpath = abspath.lstrip(rootdir)

    try:
        stats = os.stat(abspath)
        filesize = stats.st_size
        filemtime = datetime.fromtimestamp(stats.st_mtime)
    except:
        log.warn("Failed to read file stats: {}", abspath)
        filesize = -1
        filemtime = None

    paperfile = PaperCorpus()
    paperfile.doi = doistr
    paperfile.directory = directory
    paperfile.doctype = doctype
    paperfile.filename = filename
    paperfile.filebytes = filesize
    paperfile.filemtime = filemtime

    paperfile.insert(db)

    log.trace(f"Added to PostGres: {relpath}")

    return True



def filename2doi(doi: str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


def run(args: ArgumentParser):
    db = postgres.connect()

    if not os.path.isdir(args.directory):
        raise ValueError("No such directory", args.directory)

    n = 0
    pg = 0

    t2 = log.info("Recursively crawling: {}", args.directory)

    for root, subdirs, files in os.walk(args.directory):
        n = 1
        log.trace("Entering: %s" %root)

        for filename in files:
            abs_path = os.path.join(root, filename)
            if _add_to_postgres(db, abs_path, args.directory):
                pg += 1

            n += 1

            if not (n % 1000):
                log.info("Processed {} files. Added {} files to DB.", n, pg)
                db.commit()

            # Not more than debugCount per directory
            # Use -1 for no limit.
            if sett.Run.debugCount > 0 and n >= sett.Run.debugCount:
                log.note("Processed maximum {} files.", n)
                break

    db.commit()
    t2.done("Added {} files to Postgres.", pg)

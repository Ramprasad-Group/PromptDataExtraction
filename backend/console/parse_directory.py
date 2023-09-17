import os
import pylogg
from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

from backend import postgres, sett
from backend.postgres.orm import Papers, PaperTexts

from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

ScriptName = 'parse'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Parse the papers from a directory.')
    parser.add_argument(
        'directory',
        help="Path to directory in the corpus.")
    parser.add_argument(
        '-f', '--file',
        default=None,
        help="Parse a single file, useful for debugging."
    )


def _add_to_postgres(db, paper: Papers, directory: str, doctype: str,
                     para: ParagraphParser):
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


def _parse_file(db, filepath, root="") -> DocumentParser | None:
    t2 = log.trace("Parsing {}", filepath)
    # Keep count of added items for statistics.
    pg = 0
    filename = os.path.basename(filepath)

    doi = filename2doi(filename)
    directory = filepath.split("/")[-2]

    doc = PaperParser(directory, filepath)
    if doc is None:
        log.error(f"Ignore: {filepath} (Parser not found)")
        return None, pg

    try:
        doc.parse(parse_tables=False)
        log.trace("Parsed document: {}", filepath)
        log.trace("Found {} paragraphs", len(doc.paragraphs))
    except Exception as err:
        log.error("Failed to parse: {} ({})", filepath, err)
        return None, pg

    if sett.Run.debugCount > 0:
        for para in doc.paragraphs:
            print("\t", "-" * 50)
            print("\t", para.text, flush=True)

    # get the foreign key
    paper = Papers().get_one(db, {'doi': doi})

    for para in doc.paragraphs:
        if paper is None:
            log.warn(f"Paper {doi} not found in postgres.")
            break
        elif _add_to_postgres(db, paper, directory, doc.doctype, para):
            pg += 1

    db.commit()
    t2.done("Parse done ({} paragraphs found). {}",
            len(doc.paragraphs), filepath)
    return doc, pg


def filename2doi(doi: str):
    doi = doi.replace("@", "/").rstrip('.html')
    doi = doi.rstrip(".xml")
    return doi


def doi2filename(doi: str, doctype: str):
    filename = doi.replace("/", "@")
    filename = filename + "." + doctype
    return filename


def run(args: ArgumentParser):
    db = postgres.connect()

    if args.directory.endswith("/"):
        args.directory = args.directory[:-1]

    if not os.path.isdir(args.directory):
        raise ValueError("No such directory", args.directory)

    if args.file:
        sett.Run.debugCount = 1
        args.file = os.path.join(args.directory, args.file)
        return _parse_file(db, args.file)

    # Get the list of DOIs that are polymer papers and not found in the
    # paper_texts table, for a specific publisher directory.
    query = """
    SELECT * FROM (
	    SELECT p.doi, p.doctype FROM filtered_papers fp
        JOIN papers p ON p.doi = fp.doi
        WHERE p.directory = :dirname
    ) AS poly WHERE poly.doi NOT IN (
	    SELECT pt.doi FROM paper_texts pt
        WHERE pt.directory = :dirname
        AND pt."section" IS DISTINCT FROM 'abstract'
    );
    """

    dirname = os.path.basename(args.directory)

    t2 = log.info("Querying list of non-parsed DOIs for {}", dirname)
    records = postgres.raw_sql(query, {'dirname': dirname})
    t2.note("Found {} DOIs not parsed.", len(records))

    if len(records) == 0:
        return

    n = 0
    pg = 0
    total_pg = 0

    for row in tqdm(records):
        n += 1
        doi = row.doi
        doctype = row.doctype
        filename = doi2filename(doi, doctype)
        abs_path = os.path.join(args.directory, filename)
        if not os.path.isfile(abs_path):
            log.error("File not found: {}", abs_path)

        try:
            doc, pg = _parse_file(db, abs_path, args.directory)
            if doc is None:
                continue
        except Exception as err:
            log.error(f"Parse error: {abs_path} ({err})")
            continue

        total_pg += pg

        if (n-1) % 50 == 0:
            log.info("Processed {} papers. Added {} paragraphs to Postgres.",
                     n, total_pg)

        # Not more than debugCount per run
        # Use -1 for no limit.
        if sett.Run.debugCount > 0 and n >= sett.Run.debugCount:
            log.note("Processed maximum {} papers.", n)
            log.info("Added {} paragraphs to Postgres, ", total_pg)
            break


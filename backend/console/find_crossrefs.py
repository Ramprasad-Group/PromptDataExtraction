from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

import pylogg
from backend import postgres
from backend.prompt_extraction.crossref_extractor import CrossrefExtractor

ScriptName = 'find-crossrefs'

log = pylogg.New(ScriptName)


def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Extract all cross-refs from a paper and save to db.')
    

def run(args : ArgumentParser):
    db = postgres.connect()
    crf = CrossrefExtractor(db)

    # Find unique paragraphs of extracted data
    query = """
    SELECT DISTINCT (em.para_id) FROM extracted_data ed 
    JOIN extracted_properties ep ON ep.id = ed.property_id 
    JOIN extracted_materials em ON em.id = ep.material_id
    WHERE ed."method" = 'GPT-3.5'
    AND ed.property = 'bandgap'
    AND ed.confidence < 1;
    """

    t2 = log.info("Querying list of unique paragraphs.")
    records = postgres.raw_sql(query)
    t2.note("Found {} unique paras.", len(records))

    if len(records) == 0:
        return

    n = 0
    p = 0
    # Process each paragraph.
    for row in tqdm(records):
        n += 1

        # Get all other paragraphs from the paper.
        sql = """
            SELECT pt.pid, pt.id FROM paper_texts pt 
            WHERE EXISTS (
                SELECT * FROM paper_texts pt2 
                WHERE pt2.id = :para_id
                AND pt.pid = pt2.pid
            )
            -- Skip the existing ones
            AND NOT EXISTS (
                SELECT 1 FROM extracted_crossrefs ec 
                WHERE ec.para_id = pt.id
            );
        """

        paras = postgres.raw_sql(sql, para_id=row.para_id)
        for para in paras:
            # Save crossrefs/abbr of the other paragraphs
            crf.add_paragraph_crossrefs(para.id)
        p += 1

        if n > 10: break

    log.note("Updated to database: {}", p)

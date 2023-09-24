import os
import pylogg
from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

from backend import postgres, sett
from backend.postgres.orm import CuratedData, PaperTexts

from backend.parser import PaperParser
from backend.parser.document import DocumentParser
from backend.parser.paragraph import ParagraphParser

ScriptName = 'add-condition'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Add conditions to curated dataset.')


def _add_to_postgres(db, curated : CuratedData, condition : str):
    """ Update CuratedData row with condition.
    """
    curated.conditions = condition
    db.commit()
    db.close()
    return True

def run(args: ArgumentParser):
    db = postgres.connect()

    query = """
        SELECT cd.id, cd.para_id FROM curated_data cd 
        WHERE cd.conditions IS NULL and cd.property_name = 'bandgap'
    """

    records = postgres.raw_sql(query)
    if len(records) == 0:
        return

    n = 0
    pg = 0

    for row in tqdm(records):
        n += 1
        curated : CuratedData = CuratedData().get_one(db, {'id': row.id})
        para : PaperTexts = PaperTexts().get_one(db, {'id': row.para_id})

        if curated is None or para is None:
            log.error("Cannot fetch curated data or para text.")

        print(para.text)
        print("-"* 80, "\n")
        print(curated.material,
              curated.property_name, curated.property_value)
        print("-"* 80, "\n")
        
        condition = input("Condition string: ").strip()

        if condition == 'exit':
            break

        if not condition:
            continue

        if _add_to_postgres(db, curated, condition):
            pg += 1

        if sett.Run.debugCount > 0 and n >= sett.Run.debugCount:
            log.note("Processed maximum {} data.", n)
            break


    log.note("Added {} conditions to Postgres.", pg)

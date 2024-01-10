from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

import pylogg
from backend import postgres

ScriptName = 'fix-unit'

log = pylogg.New(ScriptName)


def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Fix the units extracted by the LLM pipeline as much as possible.')
    parser.add_argument(
        '--save', default=False,
        action='store_true',
        help="Commit the changes to database.")
    parser.add_argument(
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")
    
def _clean_word(word):
    word = word.strip()
    word = word.lstrip("~")
    word = word.rstrip("-")
    return word.strip()

def run(args : ArgumentParser):
    from backend.postgres import persist

    db = postgres.connect()
    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)

    query = """
    SELECT  ep.id, ep.value, ep.unit
    FROM    extracted_properties ep 
    WHERE   ep.method_id = :mid
    AND     ep.unit = '}';
    """

    log.update('line_width', 150)

    t2 = log.info("Querying list of non-processed items.")
    records = postgres.raw_sql(query, mid = method.id)
    t2.note("Found {} items not processed.", len(records))

    if len(records) == 0:
        return

    # Fetch meoh permeability units.
    meta = postgres.raw_sql("""
        Select units, stdunit From property_metadata
        Where property = 'meoh_perm';
    """)
    meoh_units = list(reversed(sorted(meta[0].units, key=len)))
    meoh_stdunit = meta[0].stdunit

    n = 0
    p = 0
    # Process each paragraph.
    for row in tqdm(records):
        n += 1
        nunit = None

        for unit in meoh_units:
            if row.value.endswith(f" {unit}"):
                nunit = meoh_stdunit
                break

        if nunit:
            sql = """
            UPDATE  extracted_properties ep
            SET     unit = :nunit
            WHERE   ep.id = :rowid;
            """
            postgres.raw_sql(sql, commit=args.save, rowid = row.id, nunit = nunit)
            log.done("{} => {}", row.value, nunit)
            p += 1
        else:
            log.warn("Unit not found for: {}", row.value)

    if args.save:
        log.note("Updated to database: {}", p)
    else:
        log.note("Updatable to database: {}", p)
        log.note("Specify --save to commit changes.")

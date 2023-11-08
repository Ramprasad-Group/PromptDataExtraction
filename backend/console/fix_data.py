from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

import pylogg
from backend import postgres

ScriptName = 'fix-data'

log = pylogg.New(ScriptName)


def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Fix the +/- extracted data as much as possible.')
    parser.add_argument(
        '--save', default=False,
        action='store_true',
        help="Commit the changes to database.")
    
def _clean_word(word):
    word = word.strip()
    word = word.lstrip("~")
    word = word.rstrip("-")
    word = word.replace("%", "")
    word = word.replace("° C", "")
    word = word.replace("°C", "")
    word = word.replace("°", "")
    return word.strip()

def run(args : ArgumentParser):
    db = postgres.connect()

    query = """
    SELECT  ep.id, ep.value, ep.numeric_value, ep.numeric_error
    FROM    extracted_properties ep 
    WHERE   ep.method_id >= 176
    -- AND     ep.value LIKE '%+/-%°C'
    AND     ep.value LIKE '%+/-%'
    AND     ep.numeric_error = 0;
    """

    t2 = log.info("Querying list of non-processed items.")

    records = postgres.raw_sql(query)

    t2.note("Found {} paragraphs not processed.", len(records))

    if len(records) == 0:
        return

    n = 0
    p = 1
    # Process each paragraph.
    for row in tqdm(records):
        n += 1
        # print("Value =", row.value)
        parts = row.value.split("+/-")

        #@todo: process values with x 10^ etc.
        if "(" in row.value and ")" in row.value:
            if "x" in row.value:
                log.warn("Cannot handle value: '{}'", row.value)
                continue
            elif "10^" in row.value:
                log.warn("Cannot handle value: '{}'", row.value)
                continue
            else:
                parts[0] = parts[0].replace("(", "")
                parts[1] = parts[1].replace(")", "")

        try:
            nvalue = float(_clean_word(parts[0]))
        except:
            log.warn("Failed to parse nvalue: '{}'", row.value)
            continue

        try:
            word = parts[1].split()[0]
            nerror = float(_clean_word(word))
        except:
            log.warn("Failed to parse nerror: '{}'", row.value)
            continue
        
        sql = """
        UPDATE  extracted_properties ep
        SET     numeric_value = :nvalue,
                numeric_error = :nerror
        WHERE   ep.id = :rowid;
        """
        postgres.raw_sql(sql, commit=args.save, rowid = row.id,
                         nvalue = nvalue, nerror = nerror)
        log.done("{} => {} +/- {}", row.value, nvalue, nerror)
        p += 1

    if args.save:
        log.note("Updated to database: {}", p)

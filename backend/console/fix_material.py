from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

import pylogg
from backend import postgres
from backend.prompt_extraction.crossref_extractor import CrossrefExtractor

ScriptName = 'fix-material'

log = pylogg.New(ScriptName)


def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Fix the materials extracted by the LLM pipeline as much as possible.')
    parser.add_argument(
        '--save', default=False,
        action='store_true',
        help="Commit the changes to database.")
    parser.add_argument(
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")


def _get_polymer(entity_name):
    # Check if a known polymer
    query = """ 
    SELECT p.norm_name, p.is_polymer, p.is_copolymer
    FROM polymers p 
    WHERE p."name" LIKE :material;
    """
    rows = postgres.raw_sql(query, material=entity_name)
    return rows[0] if rows else None


def run(args : ArgumentParser):
    from backend.postgres import persist

    db = postgres.connect()
    crf = CrossrefExtractor(db)

    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)

    # Filter all materials where class is not known
    query = """
    SELECT
        em.id, em.para_id, em.entity_name,
        em.normalized_material_name, em.coreferents
    FROM    extracted_materials em
    WHERE   em.method_id = :mid
    AND     em.material_class = '';
    """

    log.update('line_width', 150)

    t2 = log.info("Querying list of non-processed items.")
    records = postgres.raw_sql(query, mid = method.id)
    t2.note("Found {} items not processed.", len(records))

    if len(records) == 0:
        return

    n = 0
    p = 0
    # Process each material name.
    for row in tqdm(records):
        n += 1
        should_update = False
        normname = row.normalized_material_name
        corefs = row.coreferents
        material_class = ''

        # parse other abbreviations.
        crf.parse_all_paragraphs(row.para_id, persist_to_db=True)

        # Check if any abbreviation matches.
        for match in crf.list_all(row.entity_name, fuzzy_cutoff=96):
            corefs.append(match)
            log.done("Found coref: {} => {}", row.entity_name, match)
            should_update = True

        # Check if a composite
        if 'composite' in row.entity_name.lower():
            material_class = 'COMPOSITE'
            should_update = True
            log.done("Found Composite: {}", row.entity_name)

        # Check if a blend
        elif 'blend' in row.entity_name.lower():
            material_class = 'BLEND'
            should_update = True
            log.done("Found blend: {}", row.entity_name)

        # Check if a known polymer
        else:
            for name in [row.entity_name] + corefs:
                known = _get_polymer(name)
                if known:
                    normname = known.norm_name
                    if known.is_polymer:
                        material_class = 'POLYMER'
                    should_update = True
                    log.done("Norm name: {} => {}", row.entity_name, normname)
                    break

        if should_update:
            p += 1
            sql = """
            UPDATE  extracted_materials em
            SET     normalized_material_name = :normname,
                    material_class  = :pclass,
                    coreferents     = :corefs
            WHERE   em.id = :rowid;
            """
            postgres.raw_sql(
                sql, commit=args.save, rowid = row.id,
                normname = normname, pclass = material_class,
                corefs = corefs,
            )
        else:
            log.trace("Unknown material: {}", row.entity_name)

        if not (n % 100):
            log.note("Found {} / {} known materials.", p, n)

    if args.save:
        log.note("Updated to database: {}", p)
    else:
        log.note("Updatable to database: {}", p)
        log.note("Specify --save to commit changes.")

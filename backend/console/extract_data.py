import pylogg
from argparse import ArgumentParser, _SubParsersAction

from backend import postgres
from backend.postgres import persist

ScriptName = 'extract-data'

log = pylogg.New(ScriptName)


method_property_map = {
    "bandgap-gpt35-similar-full": "bandgap",
    "co2_perm-gpt35-similar-full": "co2_perm",
    "cs-gpt35-similar-full": "cs",
    "ct-gpt35-similar-full": "ct",
    "dc-gpt35-similar-full": "dc",
    "density-gpt35-similar-full": "density",
    "eab-gpt35-similar-full": "eab",
    "fs-gpt35-similar-full": "fs",
    "hardness-gpt35-similar-full": "hardness",
    "h2_perm-gpt35-similar-full": "h2_perm",
    "iec-gpt35-similar-full": "iec",
    "ionic_cond-gpt35-similar-full": "ionic_cond",
    "is-gpt35-similar-full": "is",
    "lcst-gpt35-similar-full": "lcst",
    "loi-gpt35-similar-full": "loi",
    "methanol_perm-gpt35-similar-full": "meoh_perm",
    "o2_perm-gpt35-similar-full": "o2_perm",
    "ri-gpt35-similar-full": "ri",
    "sd-gpt35-similar-full": "sd",
    "tc-gpt35-similar-full": "tc",
    "td-gpt35-similar-full": "td",
    "tm-gpt35-similar-full": "tm",
    "ts-gpt35-similar-full": "ts",
    "tg-gpt35-similar-full": "tg",
    "ucst-gpt35-similar-full": "ucst",
    "wca-gpt35-similar-full": "wca",
    "wu-gpt35-similar-full": "wu",
    "ym-gpt35-similar-full": "ym",
}

def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Filter the extracted properties based on confidence scores.')
    parser.add_argument(
        "-m", "--method", required=True,
        help="(Required) Name of the method for the extraction_methods table.")
    parser.add_argument(
        "--drop", default=False, action='store_true',
        help="Recreate intermediate views. Default: False")


def _drop_views():
    postgres.raw_sql("DROP VIEW valid_data;")
    log.warn("Dropped valid_data")
    postgres.raw_sql("DROP VIEW data_scores;")
    log.warn("Dropped data_scores")


def _create_data_scores_view():
    sql = """
    CREATE OR REPLACE VIEW data_scores AS
    SELECT
        *,
        (unit + prop + tabl + rang) AS error,
        (poly) AS score
    FROM (
        SELECT
            fd.target_id AS prop_id,
            -- negative attributes
            sum(CASE WHEN fd.filter_name = 'invalid_property_unit' 	THEN -1 ELSE 0 END) AS unit,
            sum(CASE WHEN fd.filter_name = 'invalid_property_name' 	THEN -1 ELSE 0 END) AS prop,
            sum(CASE WHEN fd.filter_name = 'is_table' 				THEN -1 ELSE 0 END) AS tabl,
            sum(CASE WHEN fd.filter_name = 'out_of_range' 			THEN -1 ELSE 0 END) AS rang,
            -- positive attributes
            sum(CASE WHEN fd.filter_name = 'is_polymer' 			THEN  1 ELSE 0 END) AS poly
        FROM filtered_data fd
        GROUP BY fd.target_id
    ) AS aggr;
    """
    postgres.raw_sql(sql)
    log.done("Recreated data_scores")


def _create_valid_data_view(method_id, method_name, prop_name):
    sql = """
    CREATE OR REPLACE VIEW valid_data AS 
    SELECT
        pt.doi,
        :mname AS "method",
        em.entity_name AS material,
        :pname AS property,
        ep.numeric_value AS value,
        ep.unit,
        ep.id AS prop_id,
        CASE
            WHEN ds.prop_id IS NOT NULL THEN ds.error ELSE 0
        END AS error,
        CASE
            WHEN ds.prop_id IS NOT NULL THEN ds.score ELSE 0
        END AS score
    FROM extracted_properties ep 
    JOIN extracted_materials em ON em.id = ep.material_id 
    JOIN paper_texts pt ON pt.id = em.para_id 
    LEFT JOIN data_score ds ON ep.id = ds.prop_id
    WHERE ep.method_id = :mid;
    """
    postgres.raw_sql(
        sql, mid = method_id, mname = method_name, pname = prop_name)
    log.done("Recreated valid_data")


def run(args : ArgumentParser):

    # Sanity check
    if args.method not in method_property_map.keys():
        raise ValueError("Method not found in property map")
    else:
        prop_name = method_property_map[args.method]

    db = postgres.connect()

    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)

    if args.drop:
        _drop_views()

    # Calculate data scores
    _create_data_scores_view()

    # Select data with good scores.
    _create_valid_data_view(method.id, method.name, prop_name)

    db.commit()


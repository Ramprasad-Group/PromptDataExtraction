import pylogg
from argparse import ArgumentParser, _SubParsersAction

from backend import postgres, sett
from backend.postgres import persist
from backend.utils import shell

ScriptName = 'extract-data'

log = pylogg.New(ScriptName)


EX_GPT_NAME = "GPT-3.5"

method_property_map = {
    "bandgap-gpt35-similar-full":       (EX_GPT_NAME, "bandgap"),
    "co2_perm-gpt35-similar-full":      (EX_GPT_NAME, "co2_perm"),
    "cs-gpt35-similar-full":            (EX_GPT_NAME, "cs"),
    "ct-gpt35-similar-full":            (EX_GPT_NAME, "ct"),
    "dc-gpt35-similar-full":            (EX_GPT_NAME, "dc"),
    "density-gpt35-similar-full":       (EX_GPT_NAME, "density"),
    "eab-gpt35-similar-full":           (EX_GPT_NAME, "eab"),
    "fs-gpt35-similar-full":            (EX_GPT_NAME, "fs"),
    "hardness-gpt35-similar-full":      (EX_GPT_NAME, "hardness"),
    "h2_perm-gpt35-similar-full":       (EX_GPT_NAME, "h2_perm"),
    "iec-gpt35-similar-full":           (EX_GPT_NAME, "iec"),
    "ionic_cond-gpt35-similar-full":    (EX_GPT_NAME, "ionic_cond"),
    "is-gpt35-similar-full":            (EX_GPT_NAME, "is"),
    "lcst-gpt35-similar-full":          (EX_GPT_NAME, "lcst"),
    "loi-gpt35-similar-full":           (EX_GPT_NAME, "loi"),
    "methanol_perm-gpt35-similar-full": (EX_GPT_NAME, "meoh_perm"),
    "o2_perm-gpt35-similar-full":       (EX_GPT_NAME, "o2_perm"),
    "ri-gpt35-similar-full":            (EX_GPT_NAME, "ri"),
    "sd-gpt35-similar-full":            (EX_GPT_NAME, "sd"),
    "tc-gpt35-similar-full":            (EX_GPT_NAME, "tc"),
    "td-gpt35-similar-full":            (EX_GPT_NAME, "td"),
    "tm-gpt35-similar-full":            (EX_GPT_NAME, "tm"),
    "ts-gpt35-similar-full":            (EX_GPT_NAME, "ts"),
    "tg-gpt35-similar-full":            (EX_GPT_NAME, "tg"),
    "ucst-gpt35-similar-full":          (EX_GPT_NAME, "ucst"),
    "wca-gpt35-similar-full":           (EX_GPT_NAME, "wca"),
    "wu-gpt35-similar-full":            (EX_GPT_NAME, "wu"),
    "ym-gpt35-similar-full":            (EX_GPT_NAME, "ym"),
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
    postgres.raw_sql("DROP VIEW valid_data;", commit=True)
    log.warn("Dropped valid_data")
    postgres.raw_sql("DROP VIEW data_scores;", commit=True)
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
            -- negative attributes (errors)
            sum(CASE WHEN fd.filter_name = 'invalid_property_unit' 	THEN -1 ELSE 0 END) AS unit,
            sum(CASE WHEN fd.filter_name = 'invalid_property_name' 	THEN -1 ELSE 0 END) AS prop,
            sum(CASE WHEN fd.filter_name = 'is_table' 				THEN -1 ELSE 0 END) AS tabl,
            sum(CASE WHEN fd.filter_name = 'out_of_range' 			THEN -1 ELSE 0 END) AS rang,
            -- positive attributes (scores)
            sum(CASE WHEN fd.filter_name = 'is_polymer' 			THEN  1 ELSE 0 END) AS poly
        FROM filtered_data fd
        GROUP BY fd.target_id
    ) AS aggr;
    """
    postgres.raw_sql(sql, commit=True)
    log.done("Recreated data_scores")


def _create_valid_data_view(method_id, method_name, prop_name):
    # Add more columns here to insert into extracted data.
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
    LEFT JOIN data_scores ds ON ep.id = ds.prop_id
    WHERE ep.method_id = :mid;
    """
    postgres.raw_sql(
        sql, commit=True, mid = method_id, mname = method_name, pname = prop_name)
    log.done("Recreated valid_data")


def _insert_to_extracted_data():
    t2 = log.info("Inserting new valid data.")
    sql = """
    INSERT INTO extracted_data (
        property_id, "method", material, property,
        value, unit, doi, confidence, date_added
    )
    SELECT
        vd.prop_id, vd."method", vd.material, vd.property,
        vd.value, vd.unit, vd.doi, vd.score, now() 
    FROM valid_data vd

    -- Ignore data with errors.
    WHERE vd.error = 0

    -- Skip already inserted ones.
    AND NOT EXISTS (
        SELECT 1 FROM extracted_data ed 
        WHERE ed.property_id = vd.prop_id
    );
    """
    postgres.raw_sql(sql, commit=True)
    t2.done("Inserted valid_data into extracted_data")


def run(args : ArgumentParser):

    # Sanity check
    if args.method not in method_property_map.keys():
        raise ValueError("Method not found in property map")
    else:
        method_name, prop_name = method_property_map[args.method]

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
    _create_valid_data_view(method.id, method_name, prop_name)

    # Insert the selected data
    _insert_to_extracted_data()


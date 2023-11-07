import argparse
import pylogg

ScriptName = 'filter-data'

log = pylogg.New(ScriptName)


filter_list = [
    'known_property',
    'unit_ok',
    'within_range',
    'is_polymer',
    'clean_text',
    'multi_methods'
]

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

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Run filters on extracted data for postprocessing.')
    parser.add_argument(
        "filter", choices = filter_list,
        help="Name of the filter to run.")
    parser.add_argument(
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")
    parser.add_argument(
        "-l", "--limit", default=100, type=int,
        help="Number of items to process. Default: 100")
    

def run(args : argparse.ArgumentParser):
    from backend import postgres
    from backend.postgres import persist
    from backend.post_process import known_property
    from backend.postgres.orm import PropertyMetadata

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


    meta = PropertyMetadata().get_one(db, dict(property = prop_name))
    if meta is None:
        raise ValueError("No property metadata defined", prop_name)


    if args.filter == 'known_property':
        validator = known_property.NameValidator(db, method, meta)
        validator.process_items(args.limit)
    elif args.filter == 'within_range':
        validator = known_property.RangeValidator(db, method, meta)
        validator.process_items(args.limit)
    elif args.filter == 'unit_ok':
        validator = known_property.UnitValidator(db, method, meta)
        validator.process_items(args.limit)
    else:
        raise ValueError("Unknown data filter", args.filter)

import argparse
import pylogg

ScriptName = 'filter-llm-data'

log = pylogg.New(ScriptName)


filter_list = [
    'all',
    'name',
    'unit',
    'range',
    'polymer',
    'table',
    'multi',
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
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")
    parser.add_argument(
        "-f", "--filter", choices = filter_list, default = 'all',
        help="Name of the filter to run.")
    parser.add_argument(
        "-l", "--limit", default=1000000, type=int,
        help="Number of items to process. Default: 1000000")
    parser.add_argument(
        "--redo", default=False, action='store_true',
        help="Reprocess all rows, ignore the last checkpoint. Default: False")
    parser.add_argument(
        "--remove", default=False, action='store_true',
        help="Remove existing rows, ignore the last checkpoint. Default: False")


def run(args : argparse.ArgumentParser):
    from backend import postgres
    from backend.postgres import persist
    from backend.post_process import known_property, known_material, known_text
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


    if args.filter == 'name':
        validator = known_property.NameValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)
    elif args.filter == 'range':
        validator = known_property.RangeValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)
    elif args.filter == 'unit':
        validator = known_property.UnitValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)
    elif args.filter == 'polymer':
        validator = known_material.PolymerSelector(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)
    elif args.filter == 'table':
        validator = known_text.TableSelector(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)
    else:
        # Run all the filters.
        validator = known_property.NameValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_property.RangeValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_property.UnitValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_material.PolymerSelector(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_text.TableSelector(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

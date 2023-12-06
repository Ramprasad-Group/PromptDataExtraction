import argparse
import pylogg

ScriptName = 'filter-ner-data'

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


def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Run filters on extracted data for postprocessing.')
    parser.add_argument(
        "-p", "--prop-id", required=True,
        help="(Required) Name of the property from the property_metadata table.")
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

    args.method = 'g-ner-pipeline'

    db = postgres.connect()

    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)

    meta = PropertyMetadata().get_one(db, dict(property = args.prop_id))
    if meta is None:
        raise ValueError("No property metadata defined", args.prop_id)

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
        validator = known_material.PolymerValidator(db, method)
        validator.process_items(args.limit, args.redo, args.remove)
    elif args.filter == 'table':
        validator = known_text.TableValidator(db, method)
        validator.process_items(args.limit, args.redo, args.remove)
    else:
        # Run all the filters.
        validator = known_property.NameValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_property.RangeValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_property.UnitValidator(db, method, meta)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_material.PolymerValidator(db, method)
        validator.process_items(args.limit, args.redo, args.remove)

        validator = known_text.TableValidator(db, method)
        validator.process_items(args.limit, args.redo, args.remove)

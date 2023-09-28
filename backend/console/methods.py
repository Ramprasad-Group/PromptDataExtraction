import pylogg
from argparse import ArgumentParser, _SubParsersAction

from backend import sett, postgres
from backend.postgres import persist

ScriptName = 'method'

log = pylogg.New(ScriptName)

def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Create or update extraction methods in database.')
    parser.add_argument(
        "subcmd", choices=['new', 'set', 'show'])
    parser.add_argument(
        "-m", "--method", required=True,
        help="(Required) Name of the method for the extraction_methods table.")
    parser.add_argument(
        "--filter", default=None,
        help="Name of the filter/para-subset to process in the method.")
    parser.add_argument(
        "--dataset", default=None,
        help="Name of the extracted dataset for the method.")
    parser.add_argument(
        "--model", default=None,
        help="Name of the model for the method.")
    parser.add_argument(
        "--api", default=None,
        help="(Optional) Name of the api for the method.")
    parser.add_argument(
        '--info', nargs='+', action='append', metavar=('key','value'),
        help="(Optional) Add/update items in extraction_info.")
    

def _try_numeric(value : str):
    """ Try to check if its a numeric value. """
    try:
        value = int(value)
    except:
        try:
            value = float(value)
        except:
            value = str(value)
    return value


def run(args : ArgumentParser):
    if args.subcmd in ['new', 'add']:
        # If method does not exist, we will create a new one.
        log.note("Creating new method: {}", args.method)
        if not args.dataset:
            log.critical("--dataset required")
            return
        if not args.model:
            log.critical("--model required")
            return
        if not args.filter:
            log.critical("--filter required")
            return

        info = {}
        info['user'] = sett.Run.userName

        if args.info:
            for k, value in args.info:
                info[k] = value[0] if type(value) == list else value
                info[k] = _try_numeric(info[k])

        db = postgres.connect()
        res = persist.add_method(db, args.method, args.dataset, args.model,
                                 args.api, args.filter, **info)
        if not res:
            log.critical("Failed to add new method.")

    elif args.subcmd in ['set', 'update']:
        # If method already exists, we will update the columns.
        log.note("Updating method: {}", args.method)
        db = postgres.connect()
        method = persist.get_method(db, name=args.method)
        if not method:
            log.critical("No such method in DB: {}", args.method)
            return

        if args.dataset:
            method.dataset = args.dataset
            log.info("dataset =", method.dataset)
        if args.model:
            method.model = args.model
            log.info("model =", method.model)
        if args.api:
            method.api = args.api
            log.info("api =", method.api)
        if args.filter:
            method.para_subset = args.filter
            log.info("para_subset =", method.para_subset)
        if args.info:
            # New dict is needed to update a sqlalchemy json field.
            info = dict(method.extraction_info)

            for k, value in args.info:
                info[k] = value[0] if type(value) == list else value
                info[k] = _try_numeric(info[k])
                log.info("extraction_info[{}] = {}", k, value)

            # Assign the new dict.
            method.extraction_info = info

        try:
            db.commit()
            log.done("Method {} has been updated in database.", args.method)
        except:
            db.rollback()
            log.critical("Failed to update method.")

    elif args.subcmd in ['view', 'show']:
        db = postgres.connect()
        method = persist.get_method(db, name=args.method)
        if not method:
            log.critical("No such method in DB: {}", args.method)
            return
        else:
            log.note("{}", method)


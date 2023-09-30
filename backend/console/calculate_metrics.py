import json
import argparse

import pylogg
from backend import sett, postgres
from backend.metrics import curated
from backend.postgres import persist

ScriptName = 'metrics'

log = pylogg.New(ScriptName)

tg_corefs = [
    'Tg', 'T_{g}', 'T_{g}s', 'T_{g})',
    'glass transition temperature',
    'glass transition temperature T_{g}',
    'the glass transition temperature',
    'glass transition', 'glass transition temperatures',
    # LLM
    'Tg',
    'T g',
    'T_g',
    'T_{g}',
    'TGA onset temperature',
    'T_{g} attributed to silicone part',
    'T_{g} (°C)',
    'T_g (cross-linked)',
    'T_g (dry)',
    'T_g (dynamic)',
    'T_g (high molecular weight polymer)',
    'T_g (low molecular weight prepolymer)',
    'T_{g} of PIC',
    'T_{g} of PTMO segments',
    'T_g (PIB)',
    'T_g (PLLA)',
    'T_g (poly[(4-MSt)-co-(4-BrMSt)])',
    'T_g range',
    'T_g (static)',
    'T_{g} values',
    'T_g (with H2O)',
    'apparent T g', 'average T_{g}',
    'glass-transition temperature',
    'glass transition temperature (°C)',
    'glass transition temperatures (T_{g}s)',
    'glass transition temperature (T_{g})',
    'glass transition temperature (T_g)',
    'glass transition temperature (Tg)',
    'glass transition (T_{g})',
    'glass transition (T_g)',
    'static Tg', 'dynamic Tg',
]

eg_corefs = [
    'bandgap', 'band gap', 'band gaps', 'E_{g}', 'E_g',
    'optical band gap', 'optical bandgap', 'band gap energies',
    'optical band gaps', 
    'band gap energy', 'optical bandgaps', 'optical band gap',
    'optical band gap energy', 'optical energy gap',
]

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Calculate metrics using curated data table.')
    parser.add_argument(
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")


def run(args : argparse.ArgumentParser):
    db = postgres.connect()

    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)


    t1 = log.info("Calculating metrics on curated dataset.")
    log.info("Method: {}", args.method)

    metrics = curated.compute_singular_metrics(tg_corefs, method)

    with open(sett.Run.directory + "/tg_metrics.json", "w") as fp:
        json.dump(metrics, fp, indent=4)

    t1.done("Tg Metrics: {}", metrics)

    log.info("=="*200)

    metrics = curated.compute_singular_metrics(eg_corefs, method)

    with open(sett.Run.directory + "/eg_metrics.json", "w") as fp:
        json.dump(metrics, fp, indent=4)

    t1.done("Eg Metrics: {}", metrics)

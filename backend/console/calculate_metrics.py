import json
import argparse

import pylogg
from backend import sett, postgres
from backend.metrics import curated

ScriptName = 'metrics'

log = pylogg.New(ScriptName)

tg_corefs = [
    'Tg', 'T_{g}', 'T_{g}s', 'T_{g})',
    'glass transition temperature',
    'glass transition temperature T_{g}',
    'the glass transition temperature',
    'glass transition', 'glass transition temperatures',
]

eg_corefs = [
    'bandgap', 'band gap', 'band gaps', 'E_{g}',
    'optical band gap', 'optical bandgap',
]

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Calculate metrics using curated data table.')

def run(args : argparse.ArgumentParser):
    db = postgres.connect()
    t1 = log.info("Calculating metrics.")

    metrics = curated.compute_metrics(db, tg_corefs, 'materials-bert')
    with open(sett.Run.directory + "/tg_metrics.json", "w") as fp:
        json.dump(metrics, fp, indent=4)
    t1.done("Metrics: {}", metrics)

    metrics = curated.compute_metrics(db, eg_corefs, 'materials-bert')
    with open(sett.Run.directory + "/eg_metrics.json", "w") as fp:
        json.dump(metrics, fp, indent=4)

    t1.done("Metrics: {}", metrics)

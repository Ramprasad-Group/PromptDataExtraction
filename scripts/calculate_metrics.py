import os
import json
import pylogg as log

from backend import postgres, sett
from backend.metrics import curated


if __name__ == '__main__':
    sett.load_settings()
    os.makedirs(sett.Run.directory, exist_ok=True)

    t1 = log.init(
        log_level=sett.Run.logLevel,
        output_directory=sett.Run.directory
    )

    log.setMaxLength(1000)

    postgres.load_settings()
    db = postgres.connect()

    tg_corefs = [
        'Tg', 'T_{g}', 'T_{g}s', 'T_{g})',
        'glass transition temperature',
        'glass transition temperature T_{g}',
        'the glass transition temperature',
        'glass transition', 'glass transition temperatures',
    ]
    metrics = curated.compute_metrics(db, tg_corefs, 'materials-bert')
    with open(sett.Run.directory + "/tg_metrics.json", "w") as fp:
        json.dump(metrics, fp)

    t1.done("Metrics: {}", metrics)
    log.close()

import os
import argparse
import pylogg as log
from backend import postgres, sett

from backend.console import (
    calculate_metrics
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    calculate_metrics.add_args(subparsers)

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    sett.load_settings()
    os.makedirs(sett.Run.directory, exist_ok=True)

    t1 = log.init(
        log_level=sett.Run.logLevel,
        output_directory=sett.Run.directory
    )
    log.setMaxLength(1000)

    postgres.load_settings()

    if args.command == 'metric':
        calculate_metrics.run(args)

    t1.done("All done.")
    log.close()


if __name__ == "__main__":
    main()
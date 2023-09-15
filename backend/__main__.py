import os
import argparse
import pylogg as log
from backend import postgres, sett

from backend.console import (
    calculate_metrics,
    checkpoint,
    db_tables,
    settings
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    calculate_metrics.add_args(subparsers)
    checkpoint.add_args(subparsers)
    db_tables.add_args(subparsers)
    settings.add_args(subparsers)

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

    if args.command == calculate_metrics.ScriptName:
        calculate_metrics.run(args)

    elif args.command == checkpoint.ScriptName:
        checkpoint.run(args)

    elif args.command == db_tables.ScriptName:
        db_tables.run(args)

    elif args.command == settings.ScriptName:
        settings.run(args)

    t1.done("All done.")
    log.close()


if __name__ == "__main__":
    main()

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

    parser.add_argument('--debug', type=int, default=0,
                        help="Debug count, override settings.yaml, default 0")
    parser.add_argument('--log', type=int, default=0,
                        help="Log level. Optional, override settings.yaml.")
    parser.add_argument('--db', default=None,
                        help="Database name. Optional, override settings.yaml.")
    parser.add_argument('--dir', default=None,
                        help="Run directory. Optional, override settings.yaml.")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    sett.load_settings()

    # Override settings.yaml
    if args.debug > 0:
        sett.Run.debugCount = args.debug

    if args.log > 0:
        sett.Run.logLevel = args.log

    if args.db:
        sett.Run.databaseName = args.db

    if args.dir:
        sett.Run.directory = args.dir

    os.makedirs(sett.Run.directory, exist_ok=True)

    t1 = log.init(
        log_level=sett.Run.logLevel,
        output_directory=sett.Run.directory,
        logfile_name=args.command + ".log",
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

    postgres.disconnect()
    t1.done("All done.")
    log.close()

if __name__ == "__main__":
    main()

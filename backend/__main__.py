import os
import argparse
import pylogg as log
from backend import postgres, sett

from backend.console import (
    calculate_metrics,
    checkpoint,
    db_tables,
    settings,
    ner_curated,
    ner_filtered,
    filter_by_ner,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Register the scripts with argparse.
    calculate_metrics.add_args(subparsers)
    checkpoint.add_args(subparsers)
    db_tables.add_args(subparsers)
    settings.add_args(subparsers)
    ner_curated.add_args(subparsers)
    ner_filtered.add_args(subparsers)
    filter_by_ner.add_args(subparsers)

    # Additional arguments for the current run.
    parser.add_argument('--debug', type=int, default=0,
                        help="Debug count, override settings.yaml, default 0")
    parser.add_argument('--log', type=int, default=0,
                        help="Log level. Optional, override settings.yaml.")
    parser.add_argument('--db', default=None,
                        help="Database name. Optional, override settings.yaml.")
    parser.add_argument('--dir', default=None,
                        help="Run directory. Optional, override settings.yaml.")
    
    # Parse arguments.
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

    # Initialize the logger.
    os.makedirs(sett.Run.directory, exist_ok=True)

    t1 = log.init(
        log_level=sett.Run.logLevel,
        output_directory=sett.Run.directory,
        logfile_name=args.command + ".log",
    )
    log.setMaxLength(1000)

    if sett.Run.debugCount > 0:
        log.note("Debug Run, Count = {}", sett.Run.debugCount)

    # Initialize configurations.
    postgres.load_settings()

    # Check and run the command against the registered scripts.
    if args.command == calculate_metrics.ScriptName:
        calculate_metrics.run(args)

    elif args.command == checkpoint.ScriptName:
        checkpoint.run(args)

    elif args.command == db_tables.ScriptName:
        db_tables.run(args)

    elif args.command == settings.ScriptName:
        settings.run(args)

    elif args.command == ner_curated.ScriptName:
        ner_curated.run(args)

    elif args.command == ner_filtered.ScriptName:
        ner_filtered.run(args)

    elif args.command == filter_by_ner.ScriptName:
        filter_by_ner.run(args)

    # Finalize.
    postgres.disconnect()
    t1.note("All done.")
    log.close()


if __name__ == "__main__":
    main()

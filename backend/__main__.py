"""
    Entrypoint for all console scripts provided by the backend package.

"""

import os
import argparse
import pylogg as log
from backend import postgres, sett

from backend.console import (
    debugger,
    calculate_metrics,
    checkpoint,
    db_tables,
    extract_llm_data,
    filter_llm_data,
    settings,
    ner_filtered,
    filter_by_ner,
    parse_directory,
    parse_corpus,
    heuristic_filter,
    add_conditions,
    ps_ner_filter,
    methods,
    llm_pipeline,
    token_count,
    fix_data,
    filter_ner_data,
    export_data,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Register the scripts with argparse.
    debugger.add_args(subparsers)
    calculate_metrics.add_args(subparsers)
    checkpoint.add_args(subparsers)
    db_tables.add_args(subparsers)
    settings.add_args(subparsers)
    ner_filtered.add_args(subparsers)
    parse_directory.add_args(subparsers)
    parse_corpus.add_args(subparsers)
    heuristic_filter.add_args(subparsers)
    add_conditions.add_args(subparsers)
    ps_ner_filter.add_args(subparsers)
    methods.add_args(subparsers)
    llm_pipeline.add_args(subparsers)
    token_count.add_args(subparsers)
    fix_data.add_args(subparsers)
    filter_llm_data.add_args(subparsers)
    filter_ner_data.add_args(subparsers)
    filter_by_ner.add_args(subparsers)
    extract_llm_data.add_args(subparsers)
    export_data.add_args(subparsers)

    # Additional arguments for the current run.
    parser.add_argument('--dir', default=None,
                        help="Output directory. Optional, overrides settings.")
    parser.add_argument('--debug', type=int, default=0,
                        help="Debug count. Optional, overrides settings.")
    parser.add_argument('--log', type=int, default=0,
                        help="Log level. Optional, overrides settings.")
    parser.add_argument('--db', default=None,
                        help="Database name. Optional, overrides settings.")
    parser.add_argument('--logfile', default=None,
                        help="Optional logfile name.")
    
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
        logfile_name=args.logfile if args.logfile else args.command + ".log",
    )
    log.setMaxLength(1000)

    if sett.Run.debugCount > 0:
        log.note("Debug Run, Count = {}", sett.Run.debugCount)

    # Initialize configurations.
    postgres.load_settings()

    # Check the command against the registered scripts and run.
    if args.command == debugger.ScriptName:
        debugger.run(args)

    elif args.command == calculate_metrics.ScriptName:
        calculate_metrics.run(args)

    elif args.command == checkpoint.ScriptName:
        checkpoint.run(args)

    elif args.command == db_tables.ScriptName:
        db_tables.run(args)

    elif args.command == settings.ScriptName:
        settings.run(args)

    elif args.command == ner_filtered.ScriptName:
        ner_filtered.run(args)

    elif args.command == filter_by_ner.ScriptName:
        filter_by_ner.run(args)

    elif args.command == parse_directory.ScriptName:
        parse_directory.run(args)

    elif args.command == parse_corpus.ScriptName:
        parse_corpus.run(args)

    elif args.command == heuristic_filter.ScriptName:
        heuristic_filter.run(args)

    elif args.command == add_conditions.ScriptName:
        add_conditions.run(args)

    elif args.command == ps_ner_filter.ScriptName:
        ps_ner_filter.run(args)

    elif args.command == methods.ScriptName:
        methods.run(args)

    elif args.command == llm_pipeline.ScriptName:
        llm_pipeline.run(args)

    elif args.command == token_count.ScriptName:
        token_count.run(args)

    elif args.command == fix_data.ScriptName:
        fix_data.run(args)

    elif args.command == filter_llm_data.ScriptName:
        filter_llm_data.run(args)

    elif args.command == filter_ner_data.ScriptName:
        filter_ner_data.run(args)

    elif args.command == extract_llm_data.ScriptName:
        extract_llm_data.run(args)

    elif args.command == export_data.ScriptName:
        export_data.run(args)


    # Finalize.
    postgres.disconnect()
    t1.note("All done.")
    log.close()


if __name__ == "__main__":
    main()

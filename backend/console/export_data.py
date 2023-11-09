import os
import shutil
from datetime import datetime
from argparse import ArgumentParser, _SubParsersAction

import pylogg
from backend import sett, postgres
from backend.utils import shell

ScriptName = 'export-data'

log = pylogg.New(ScriptName)


def add_args(subparsers : _SubParsersAction):
    """ Add module specific arguments. """
    parser : ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Filter the extracted properties based on confidence scores.')
    parser.add_argument(
        "-t", "--table", default="extracted_data",
        help="Name of the table to export. Default: extracted_data")
    parser.add_argument(
        "-d", "--outdir", default=None,
        help="Name of the directory to export to.")
    parser.add_argument(
        "-o", "--overwrite", default=False, action='store_true',
        help="Delete existing export directory.")
    parser.add_argument(
        "-f", "--format", default='dump', choices=['dir', 'sql', 'tar', 'dump'],
        help="Export format. Default: dump")


def run(args : ArgumentParser):
    if args.outdir is None:
        today = "{:%b%d_%Y}".format(datetime.now())
        args.outdir = os.path.join(".", "exports", today, sett.PostGres.db_name)

    if args.overwrite:
        if args.outdir == ".":
            raise ValueError("Cannot recursively remove .")
        shutil.rmtree(args.outdir)
        log.warn("Recursively deleted existing directory: {}", args.outdir)

    os.makedirs(args.outdir, exist_ok=True)
    log.info("Created export directory: {}", args.outdir)

    if args.format == 'sql':
        outfile = os.path.join(args.outdir, f"{args.table}.sql")
        dump_opt = f'-F p -f {outfile}'   # plain text file, serial
        log.info("Exporting in plain text / SQL format")
    elif args.format == 'tar':
        outfile = os.path.join(args.outdir, f"{args.table}.sql.tar")
        dump_opt = f'-F t -f {outfile}'   # plain text file, serial
        log.info("Exporting in plain / TAR format")
    elif args.format == 'dump':
        outfile = os.path.join(args.outdir, f"{args.table}.pgdump")
        dump_opt = f'-F c -f {outfile}'   # plain text file, serial
        log.info("Exporting in compressed / custom format")
    else:
        dump_opt = f'-j 4 -F d -f {args.outdir}'   # directory, parallel
        log.info("Exporting in pgdump / directory format")

    host = sett.PostGres.db_host
    port = sett.PostGres.db_port

    postgres.connect()

    if postgres.SSH:
        host = postgres.SSH.local_bind_host
        port = postgres.SSH.local_bind_port

    cmd = f"pg_dump -v -U {postgres.db.user} -h {host} -p {port} "\
          f"{dump_opt} -d {postgres.db.name} "\
          f"-t {args.table}"

    # Execute pg_dump
    log.note("Executing command: {}", cmd)
    proc = shell.execute_command(cmd)
    if proc.returncode == 0:
        log.done("Table {} exported to {}", args.table, args.outdir)
        for line in str(proc.stdout).splitlines():
            log.info(line)
    else:
        log.error("Failed to export table {}", args.table)
        log.error("{}", str(proc.stderr))

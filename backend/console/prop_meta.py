"""
Create or update new property metadata
"""

import argparse
import pylogg

ScriptName = 'prop-meta'

log = pylogg.New(ScriptName)

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Create or update property metadata.')
    parser.add_argument(
        "task", choices=['pull', 'push'],
        help="Task to execute.")
    parser.add_argument(
        "-p", "--prop", required=True,
        help="Property from the property_metadata table.")
    parser.add_argument(
        "-f", "--file", default="property.txt",
        help="Input/Output file name.")
    parser.add_argument(
        "-u", "--update", default=False, action='store_true',
        help="Update instead of appending new names.")


def run(args : argparse.ArgumentParser):
    from backend import postgres
    from backend.postgres.orm import PropertyMetadata

    db = postgres.connect()

    meta : PropertyMetadata = PropertyMetadata().get_one(db, dict(property = args.prop))
    if meta is None:
        raise ValueError("No property metadata defined", args.prop)

    if args.task == 'pull':
        # get the property other names into a file
        with open(args.file, 'w') as fp:
            fp.writelines([l + "\n" for l in meta.other_names])

        print("Save OK:", args.file)
    
    elif args.task == 'push':
        # update property other names from a file to the database.
        with open(args.file) as fp:
            lines = [l.strip() for l in fp.readlines() if len(l.strip())]
        
        if args.update:
            existing = []
        else:
            existing = list(meta.other_names)

        n = 0
        for line in lines:
            if line not in existing:
                n += 1
                existing.append(line)
                log.info("Add new name: {}", line)

        if n > 0:
            meta.other_names = existing
            db.commit()
        else:
            log.note("No new names to add.")


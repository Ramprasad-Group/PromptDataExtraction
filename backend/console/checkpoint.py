import argparse
import pylogg

from backend import postgres
from backend.postgres import checkpoint

ScriptName = 'ckpt'

log = pylogg.New(ScriptName)

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Add, list current checkpoints in table_cursor')
    parser.add_argument('name', help="Process name")
    parser.add_argument('table', help="Table name")
    parser.add_argument('-r', '--row', type=int, default=0,
                        help="Max row processed")
    parser.add_argument('-c', '--comment', default=None, help="Comment string")
    parser.add_argument('-l', '--list', default=False, help="List all",
                        action='store_true')
    parser.add_argument('-g', '--get', default=False, help="Get last max row",
                        action='store_true')
    
def run(args : argparse.ArgumentParser):
    db = postgres.connect()

    if args.list:
        history = checkpoint.list_all(db, args.name, args.table, args.comment)
        for item in history:
            print(f"\nName: {item.name}, Table: {item.table}, Row: {item.row}")
            if item.comment:
                print(f"Comment: {item.comment}")
            print("-"*50)
        if not history:
            print("No history found.")

    if args.get:
        last = checkpoint.get_last(db, args.name, args.table, args.comment)
        print(f"\nTable: {args.table}, Last ID: {last}, Comment: {args.comment}")

    if not args.list and not args.get:
        checkpoint.add_new(db, args.name, args.table, args.row, args.comment)

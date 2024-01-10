import argparse
import pylogg

from backend import postgres
from backend.postgres import orm

ScriptName = 'pgtables'

log = pylogg.New(ScriptName)

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser = subparsers.add_parser(
        ScriptName,
        help='Create all new PostGres tables defined by the ORM.')
    
def run(args : argparse.ArgumentParser):
    # Create all tables if not already created
    orm.ORMBase.metadata.create_all(postgres.engine())
    print("Tables processed. Done!")

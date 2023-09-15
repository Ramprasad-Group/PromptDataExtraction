import argparse
import pylogg

from backend import postgres
from backend import sett

ScriptName = 'sett'

log = pylogg.New(ScriptName)

def add_args(subparsers : argparse._SubParsersAction):
    """ Add module specific arguments. """
    parser : argparse.ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Create or update the settings.yaml file.')
    parser.add_argument('-i', '--input',
                        default="settings.yaml",
                        help="Input settings.yaml file.")
    parser.add_argument('-o', '--output',
                        default="settings.yaml",
                        help="Output settings.yaml file.")
    
def run(args : argparse.ArgumentParser):
    try: sett.load_settings(settings_yaml=args.input)
    except: pass
    sett.save_settings(settings_yaml=args.output)

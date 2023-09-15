import os, sys
import argparse
import pylogg as log
from backend import postgres, sett

COMMANDS = [
    'cursor',
    'metric',
    'migrate',
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help="Name of the command",
                        choices=COMMANDS)
    args = parser.parse_args()
    return args

def init(args):
    sett.load_settings()
    os.makedirs(sett.Run.directory, exist_ok=True)

    t1 = log.init(
        log_level=sett.Run.logLevel,
        output_directory=sett.Run.directory
    )

    log.setMaxLength(1000)

    postgres.load_settings()
    db = postgres.connect()

    t1.done("All done.")
    log.close()

def main():
    args = parse_args()
    init(args)

if __name__ == "__main__":
    main()
import os
import pylogg
from argparse import ArgumentParser, _SubParsersAction

ScriptName = 'debugger'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Run debugger on a class or pipeline, edit the script first.')


def run(args: ArgumentParser):
    from backend import postgres, sett
    from backend.postgres.orm import ExtractedProperties
    from backend.prompt_extraction.property_extractor import PropertyDataExtractor

    # Debugging
    pylogg.setConsoleStack(show=True)
    pylogg._conf.line_width = 150
    pylogg.setLevel(pylogg.Level.DEBUG)

    db = postgres.connect()

    exct = PropertyDataExtractor(db, sett.DataFiles.properties_json)

    p = exct.parse_property('test', 'ranged from 333 up to 400 °C under air')
    print(p)

    props : list[ExtractedProperties] = ExtractedProperties().get_all(db)

    print("Fetched %d properties from db" %len(props))

    missed = [
    ]

    for i, prop in enumerate(props):
        if missed and i not in missed:
            continue

        print(i, "name=", prop.entity_name)
        print("value=", prop.value)
        exprop = exct.parse_property(prop.entity_name, prop.value)

        if exprop is None:
            print("!! Not a valid record. !!")
        else:
            print("numeric=", exprop.property_numeric_value,
              "unit=", exprop.property_unit)
            print("conditions=", exprop.condition_str)
    
        print("-" * 80, "\n")

        # input("Press enter to continue ...")

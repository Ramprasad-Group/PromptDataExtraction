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

    db = postgres.connect()

    exct = PropertyDataExtractor(db, sett.DataFiles.properties_json)

    p = exct.parse_property('test', '131 °C for P1 and 152 °C for P2')
    print(p)


    # props : list[ExtractedProperties] = ExtractedProperties().get_all(db)

    # print("Fetched %d properties from db" %len(props))

    # missed = [3, 4, 5, 7, 8, 9, 11, 22, 24, 33, 41, 44, 45, 54, 57,
    #           58, 59, 67, 77, 98, 99, 113, 126, 137, 138, 143, 155,
    #           156, 159, 160, 167, 185, 199
    # ]

    # for i, prop in enumerate(props):
    #     if i not in missed:
    #         continue

    #     print(i, "name=", prop.entity_name)
    #     exprop = exct.parse_property(prop.entity_name, prop.value)

    #     print("value=", prop.value, "numeric=", exprop.property_numeric_value,
    #           "unit=", exprop.property_unit)
    #     print("-" * 80, "\n")

    #     # input("Press enter to continue ...")

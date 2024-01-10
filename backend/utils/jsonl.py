import json

def read_file(jsonl_file : str) -> list[dict]:
    """ Load a JSONL file into list of dictionaries. """
    with open(jsonl_file) as fp:
        jsonlines = list(fp)

    return [ json.loads(json_str) for json_str in jsonlines ]


def save_file(linelist : list[dict] , jsonl_file : str):
    """ Save a list of dictionaries as a JSONL file. """

    # Make sure all dict items have the same keys.
    keys = set()
    for line in linelist:
        for k in line.keys():
            keys.add(k)

    # Add the missing ones with None.
    for line in linelist:
        for k in keys:
            if k not in line:
                line[k] = None

    jsonlines = [ json.dumps(line) + "\n" for line in linelist ]
    with open(jsonl_file, "w") as fp:
        fp.writelines(jsonlines)

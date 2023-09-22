import json

def read_file(jsonl_file : str) -> list[dict]:
    """ Load a JSONL file into list of dictionaries. """
    with open(jsonl_file) as fp:
        jsonlines = list(fp)

    return [ json.loads(json_str) for json_str in jsonlines ]


def save_file(linelist : list[dict] , jsonl_file : str):
    """ Save a list of dictionaries as a JSONL file. """
    jsonlines = [ json.dumps(line) + "\n" for line in linelist ]
    with open(jsonl_file, "w") as fp:
        fp.writelines(jsonlines)

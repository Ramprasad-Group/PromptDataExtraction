#!/usr/bin/env python
""" Yaml based configuration management.
    Execute this script directly to create the yaml settings file.

    Settings are grouped by sections defined below.
"""


import yaml

class Settings:
    def __init__(self, init_dict : dict = {}) -> None:
        assert type(init_dict) == dict
        self.__dict__['_items'] = init_dict

    def __getattr__(self, key : str) -> any:
        return self._items[key]

    def __setattr__(self, key : str, value):
        self._items[key] = value

    def __getitem__(self, key : str) -> any:
        return self._items[key]

    def __setitem__(self, key : str, value):
        if type(key) != str:
            raise KeyError(key)
        self._items[key] = value

    def __dir__(self) -> list:
        return self._items.keys()


# Default values
Run  = Settings({
    'name': 'test',
    'debug': True,
    'db_update': False,
    'outdir': 'test',
    'logfile': 'test.log',
})

WebUI  = Settings({
    'name': 'PromptDataExtract',
})

FullTextParse = Settings({
    'paper_corpus_root_dir': None,
    'mongodb_collection': 'polymer_DOI_records_dev',
})

Database  = Settings({
    'type': 'mongodb',
})

Dataset  = Settings({
    'tg_ground_xl': 'data/glass_transition_temperature/glass_transition_temperature_curated_data.xlsx',
    'bandgap_ground_xl': 'data/bandgap/bandgap_curated_data.xlsx',
    'tg_extracted_csv': 'data/glass_transition_temperature/glass_transition_temperature_extracted_data.csv',
    'bandgap_extracted_csv': 'data/bandgap/bandgap_extracted_data.csv',
    'psc_ground_extracted_xl': 'data/polymer_solar_cells/polymer_solar_cell_extracted_data_curated.xlsx',
    'polymer_nen_json': 'data/normalized_polymer_dictionary.json',
    'properties_json': 'data/property_metadata.json',
    'llm_properties_xl': 'data/Polymer-Property-List.xlsx',
    'rop_fulltext_xl': 'data/rop_fulltexts.xlsx',
})

LanguageModel = Settings({
    'openai_key': None,
    'polyai_key': 'pl-test',
    'llm': 'openai',
    'langchain_debug': True,
})

NerModel = Settings({
    'model': 'models/MaterialsBERT',
    'local': True,
    'pytorch_device': 0,
})

MongoDb = Settings({
    'sshtunnel': False,
    'host': 'localhost',
    'port': 5455,
    'dbname': 'test',
    'username': None,
    'password': None,
    'authSource': None,
    'collection': 'test',
})

PostGres = Settings({
    'ssh_host': '',
    'ssh_user': '',
    'ssh_pass': '',
    'ssh_port': 22,
    'db_host': 'localhost',
    'db_port': 5454,
    'db_name': 'test',
    'db_user': None,
    'db_pswd': None,
})

# Settings for LLM based extraction from abstracts.
PEAbstract = Settings({
    'property': 'Tg',
    'doi_error_list_file': 'doi_error_list.json',
    'n_shots': 1,
    'prompt': 5,
    'shot_sampling': 'baseline_diversity',
    'mongodb_collection': 'modular_run_4',
})

# Settings for LLM based extraction from the full text.
PEFullText = Settings({
    'doi_error_list_file': 'doi_error_list.json',
    'n_shots': 1,
    'prompt': 5,
    'shot_sampling': 'baseline_diversity',
    'mongodb_collection': 'polymer_DOI_records_dev',
})


def load_settings(settings_yaml: str = 'settings.yaml') -> bool:
    """ Load settings from a yaml file. """
    _yaml = {}
    try:
        with open(settings_yaml) as fp:
            _yaml = yaml.safe_load(fp)
            print("Load OK:", settings_yaml)
    except: return False

    Run._items.update(_yaml.get('Run', {}))
    WebUI._items.update(_yaml.get('WebUI', {}))
    Dataset._items.update(_yaml.get('Dataset', {}))
    Database._items.update(_yaml.get('Database', {}))
    NerModel._items.update(_yaml.get('NerModel', {}))
    LanguageModel._items.update(_yaml.get('LanguageModel', {}))
    MongoDb._items.update(_yaml.get('MongoDb', {}))
    PostGres._items.update(_yaml.get('PostGres', {}))
    PEAbstract._items.update(_yaml.get('PEAbstract', {}))
    PEFullText._items.update(_yaml.get('PEFullText', {}))
    FullTextParse._items.update(_yaml.get('FullTextParse', {}))
    return True


def save_settings(settings_yaml: str = 'settings.yaml'):
    """ Save current settings to a yaml file. """
    d = {
        'Run': Run._items,
        'WebUI': WebUI._items,
        'Dataset': Dataset._items,
        'Database': Database._items,
        'NerModel': NerModel._items,
        'LanguageModel': LanguageModel._items,
        'MongoDb': MongoDb._items,
        'PostGres': PostGres._items,
        'PEAbstract': PEAbstract._items,
        'PEFullText': PEFullText._items,
        'FullTextParse': FullTextParse._items,
    }

    with open(settings_yaml, 'w+') as fp:
        yaml.safe_dump(d, fp, sort_keys=False, indent=4)
        print("Save OK:", settings_yaml)


if __name__ == '__main__':
    # Execute directly to create the sample settings.yaml file.
    try: load_settings()
    except: pass
    save_settings()

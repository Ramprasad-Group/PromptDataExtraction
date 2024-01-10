""" Yaml based configuration management.
    Execute this script directly to create the yaml settings file.

    Settings are grouped by sections defined below.
"""
import yaml
from dataclasses import dataclass

from backend.sett import sections

_sections : list = []

Run = sections.run()
NERPipeline = sections.ner_pipeline()
FullTextParse = sections.full_text_parse()
LLMPipeline = sections.llm_pipeline()
MongoDb = sections.mongo_config()
PostGres = sections.postgres_config()
WebUI = sections.webui()
DataFiles = sections.data_files()


# List of sections in the YAML file.
_sections = [
    Run,
    NERPipeline,
    FullTextParse,
    LLMPipeline,
    MongoDb,
    PostGres,
    WebUI,
    DataFiles,
]

def load_settings(settings_yaml: str = 'settings.yaml') -> bool:
    """ Load settings from a yaml file. Returns True if load was successful. """
    _yaml = {}
    try:
        with open(settings_yaml) as fp:
            _yaml = yaml.safe_load(fp)
            print("Load OK:", settings_yaml)
    except: return False
    
    for section in _sections:
        section.__dict__.update(
            _yaml.get(section.__class__.__name__, section.__dict__))

    return True


def save_settings(settings_yaml: str = 'settings.yaml'):
    """ Save current settings to a yaml file. """
    d = {
        section.__class__.__name__ : section.__dict__
        for section in _sections
    }

    with open(settings_yaml, 'w') as fp:
        yaml.safe_dump(d, fp, sort_keys=False, indent=4)
        print("Save OK:", settings_yaml)


def load_section(
        section : dataclass, settings_yaml: str = 'settings.yaml') -> dataclass:
    """ Load a named section from the settings yaml file. Use this to load
        a custom settings section from the yaml file.
    """
    _yaml = {}
    try:
        with open(settings_yaml) as fp:
            _yaml = yaml.safe_load(fp)
            print("Load OK:", settings_yaml)
    except: return False
    
    section.__dict__.update(
        _yaml.get(section.__class__.__name__, section.__dict__))

    return section


def save_section(
        section : dataclass, settings_yaml: str = 'settings.yaml'):
    """ Save a named section to the settings yaml file. Use this to save
        a custom settings dataclass to the yaml file.
    """
    d = {}
    try:
        with open(settings_yaml) as fp:
            d = yaml.safe_load(fp)
    except:
        pass
    
    d[section.__class__.__name__] = section.__dict__

    with open(settings_yaml, 'w') as fp:
        yaml.safe_dump(d, fp, sort_keys=False, indent=4)
        print("Save OK:", settings_yaml)



if __name__ == '__main__':
    # Execute directly to create the sample settings.yaml file.
    try: load_settings()
    except: pass
    save_settings()


""" Class definitions for the setting sections. """

from dataclasses import dataclass


@dataclass
class run:
    directory : str = 'test'
    """ Output directory for the current run."""

    debugCount : int = 10
    """ Enable debug mode if > 0. """

    logLevel : int = 8
    """ Logging level, higher is more verbose.
        8 = Debug
        7 = Trace
        6 = Info etc.
    """

    databaseName : str = 'polylet'
    """ PostGres database to use for current run. """

    userName : str = ''
    """ User name or email to store into database. """


@dataclass
class ner_pipeline:
    model : str = 'models/MaterialsBERT'
    """ Path to the BERT model, or name of the BERT model in HF hub. """

    pytorch_device : int = 0
    """ GPU id to load the BERT model. """

    mongodb_collection : str = 'modular_run_4'
    """ Mongodb ground/curated dataset collection. """



@dataclass
class full_text_parse:
    paper_corpus_root_dir : str = None
    """ Path to the corpus directory. """

    add2postgres : bool = True
    """ Whether to add parsed items to postgres."""


@dataclass
class llm_pipeline:
    # Settings for LLM based extraction from abstracts.
    openai_key : str = None
    polyai_key : str = 'pl-test'
    llm : str = 'openai'
    n_shots : int = 1
    prompt : int = 5
    property : str = 'Tg'
    doi_error_list_file : str = 'doi_error_list.json'
    shot_sampling : str = 'baseline_diversity'
    mongodb_collection : str = 'modular_run_4'


@dataclass
class mongo_config:
    host : str = 'localhost'
    """ localhost or ganaam4.mse.gatech.edu """
    port : int = 8161
    dbname : str = 'polymer_records'
    username : str = 'admin'
    password : str = 'EntyWeSTEREc'
    authSource : str = 'polymer_records'
    collection : str = 'polymer_records'


@dataclass
class postgres_config:
    ssh_host : str = ''
    """ If defined, SSH tunnel will be established, else localhost assumed. """
    ssh_user : str = ''
    ssh_pass : str = ''
    ssh_port : int = 22
    db_host : str = 'localhost'
    db_port : str = 5454
    db_name : str = 'polylet'
    db_user : str = None
    db_pswd : str = None


@dataclass
class webui:
    header : str = "PromptDataExtract"
    """ Heading for the web UI home page."""


@dataclass
class data_files:
    polymer_nen_json: str = "data/normalized_polymer_dictionary.json"
    """ Path to JSON file containing normalized polymer names. """

    properties_json: str = "data/property_metadata.json"
    """ Path to JSON file containing property metadata. """

    llm_properties_xl: str = "data/Polymer-Property-List.xlsx"
    """ Path to excel file containing list of properties to extract data from. """

    tg_ground_xl: str = "data/glass_transition_temperature/glass_transition_temperature_curated_data.xlsx"
    """ """

    bandgap_ground_xl: str = "data/bandgap/bandgap_curated_data.xlsx"
    """ """

    tg_extracted_csv: str = "data/glass_transition_temperature/glass_transition_temperature_extracted_data.csv"
    """ """

    bandgap_extracted_csv: str = "data/bandgap/bandgap_extracted_data.csv"
    """ """

    psc_ground_extracted_xl: str = "data/polymer_solar_cells/polymer_solar_cell_extracted_data_curated.xlsx"
    """ """

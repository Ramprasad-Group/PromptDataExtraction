# Available Scripts
These scripts can be run via the command line.

To see the list of available commands, run
```sh
python backend -h
```

To see the help info for a specific command, run
```sh
python backend <command> -h
```

## Description of the commands

- `sett`: update the settings.yaml file using sections definitions.

- `pgtables`: update database tables using ORM definitions.

- `ner-curated`: run ner data extraction pipeline on the text related to
    curated dataset.

- `metrics`: calculate metrics on the extracted data against the curated data.

- `filter-by-ner`: go through available paragraphs in database, and filter
    them by ner.

- `ner-filtered`: run ner data extraction pipeline on the ner-filtered texts.


## Workflow
1. Create the setting.yaml file by running the `sett` command.
2. Run `filter-by-ner` to filter out the texts/paragraphs that passes the NER
    filter.
3. Run `ner-filtered` to run data extraction pipeline on the ner-filtered texts.
4. Extracted data are stored in `extracted_*` tables in the database.

import pylogg
from argparse import ArgumentParser, _SubParsersAction

ScriptName = 'ner-curated'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Run NER pipeline on curated data rows.')
    parser.add_argument(
        'runname',
        help="Name of the run, e.g., test-ner-pipeline.")


def run(args: ArgumentParser):
    from backend import postgres, sett
    from backend.postgres.orm import CuratedData, PaperTexts
    from backend.record_extraction import bert_model, pipeline, utils

    db = postgres.connect()

    extraction_info = {
        'method': 'materials-bert',
        'dataset': 'curated',
        'runname': args.runname,
    }

    # Load NEN dataset and property metadata.
    nd = utils.LoadNormalizationDataset(sett.DataFiles.polymer_nen_json)
    norm_dataset = nd.process_normalization_files()
    prop_metadata = utils.load_property_metadata(
        sett.DataFiles.properties_json)

    # Load Materials bert to GPU
    bert = bert_model.MaterialsBERT(sett.NERPipeline.model)
    bert.init_local_model(device=sett.NERPipeline.pytorch_device)

    log.info("Running NER pipeline on curated dataset.")
    log.info("Extraction info = {}", extraction_info)

    n = 0
    # Process each paragraph linked to the curated data.
    for data in next(CuratedData().iter(db, size=100)):
        n += 1
        print(n, data.doi)

        if sett.Run.debugCount > 0 and n >= sett.Run.debugCount:
            break

        paragraph = PaperTexts().get_one(db, {'id': data.para_id})

        if sett.Run.debugCount > 0:
            print(paragraph.text)

        pipeline.process_paragraph(
            db, bert, norm_dataset, prop_metadata,
            extraction_info, paragraph)

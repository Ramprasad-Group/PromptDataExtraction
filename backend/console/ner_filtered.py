import pylogg
from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

ScriptName = 'ner-filtered'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Run NER pipeline on the ner-filtered paragraph rows.')
    parser.add_argument(
        "-r", "--runname", default='ner-pipeline',
        help="Optional name of the run. Default: ner-pipeline")
    parser.add_argument(
        "-l", "--limit", default=100000, type=int,
        help="Number of paragraphs to process. Default: 100000")


def run(args: ArgumentParser):
    from backend import postgres, sett
    from backend.utils import checkpoint
    from backend.postgres.orm import FilteredParagraphs, PaperTexts
    from backend.record_extraction import bert_model, pipeline, utils

    db = postgres.connect()

    extraction_info = {
        'method':  'materials-bert',
        'dataset': 'ner-filter',
        'runname': args.runname,
    }

    runinfo = {
        'user': sett.Run.userName,
        'filter_name': 'ner_filter',
    }

    # Last processed row.
    last = checkpoint.get_last(
        db, args.runname, FilteredParagraphs.__tablename__, runinfo)
    log.info("Last run row ID: {}", last)

    query = """
    SELECT * FROM (
        --Get the para ids of the filtered paragraphs.
        SELECT fp.id AS filter_id, pt.id AS para_id
        FROM filtered_paragraphs fp JOIN paper_texts pt ON fp.para_id = pt.id 
        WHERE fp.id > :last AND fp.filter_name = 'ner_filter'
        ORDER BY fp.id LIMIT :limit
    ) AS ft
    --Ingore previously processed ones.
    WHERE NOT EXISTS (
        SELECT 1 FROM extracted_materials em
        WHERE em.para_id = ft.para_id
    ) AND NOT EXISTS (
        SELECT 1 FROM extracted_material_amounts ema
        WHERE ema.para_id = ft.para_id
    );
    """

    t2 = log.info("Querying list of non-processed NER filtered paragraphs.")
    records = postgres.raw_sql(query, {'last': last, 'limit': args.limit})
    t2.note("Found {} paragraphs not parsed.", len(records))

    if len(records) == 0:
        return
    else:
        log.note("Unprocessed Row IDs: {} to {}",
                 records[0].filter_id, records[-1].filter_id)

    # Load NEN dataset and property metadata.
    nd = utils.LoadNormalizationDataset(sett.DataFiles.polymer_nen_json)
    norm_dataset = nd.process_normalization_files()
    prop_metadata = utils.load_property_metadata(
        sett.DataFiles.properties_json)

    # Load Materials bert to GPU
    bert = bert_model.MaterialsBERT()
    bert.init_local_model(
        sett.NERPipeline.model, sett.NERPipeline.pytorch_device)

    log.info("Running NER pipeline on filtered paragraphs.")
    log.info("Extraction info = {}", extraction_info)
    log.info("Run info = {}", runinfo)

    n = 0
    # Process each paragraph linked to the curated data.
    for row in tqdm(records):
        n += 1
        if row.filter_id < last:
            continue

        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            break

        # Fetch the paragraph.
        paragraph = PaperTexts().get_one(db, {'id': row.para_id})

        if sett.Run.debugCount > 0:
            print(paragraph.text)

        try:
            pipeline.process_paragraph(
                db, bert, norm_dataset, prop_metadata,
                extraction_info, paragraph)
        except Exception as err:
            log.error("Failed to process paragraph {}: {}", row.para_id, err)
            if sett.Run.debugCount > 0:
                raise err
        
        last = row.filter_id

        if not (n % 50) or n == len(records):
            log.info("Processed {} paragraphs.", n)


    # Store the last processed id.
    log.note("Last processed row ID: {}", last)
    checkpoint.add_new(
        db, args.runname, FilteredParagraphs.__tablename__, last, runinfo)

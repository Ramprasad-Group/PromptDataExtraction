import pylogg
from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

ScriptName = 'llm-pipeline'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Run LLM pipeline defined by a specific method.')
    parser.add_argument(
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")
    parser.add_argument(
        '--rebuild', default=False,
        action='store_true',
        help="Rebuild the curated dataset and recompute the embeddings.")
    parser.add_argument(
        "-l", "--limit", default=1000, type=int,
        help="Number of paragraphs to process. Default: 1000")


def run(args: ArgumentParser):
    import openai
    from backend import postgres, sett
    from backend.postgres import persist, checkpoint
    from backend.postgres.orm import FilteredParagraphs, PaperTexts
    from backend.prompt_extraction.pipeline import LLMPipeline

    # Debugging
    # pylogg.setConsoleStack(show=True)
    # pylogg._conf.line_width = 150

    db = postgres.connect()

    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)

    log.info("Method LLM extraction configuration: {}", method.extraction_info)

    if method.api == 'openai':
        assert sett.LLMPipeline.openai_key is not None, \
            "openai_key is not set in the settings file."
        openai.api_key = sett.LLMPipeline.openai_key

    elif method.api == 'polyai':
        try:
            import polyai.api
        except:
            log.critical("Failed to import polyai, make sure it's installed.")
            exit(1)

        assert sett.LLMPipeline.polyai_key, \
            "polyai_key is not set in the settings file."
        polyai.api.api_key = sett.LLMPipeline.polyai_key

    else:
        log.warn("No api being used.")
        # log.critical("Unrecognized api '{}' defined in the method {}",
        #              method.api, args.method)
        # exit(1)


    para_filter_name = method.para_subset
    ckpt_info = {
        'user': sett.Run.userName,
        'method': method.name,
        'filter_name': para_filter_name,
    }

    # Last processed row.
    last = checkpoint.get_last(
        db, method.name, FilteredParagraphs.__tablename__, ckpt_info)
    log.info("Last run row ID: {}", last)

    query = """
    --Get the para ids of the filtered paragraphs.
    SELECT * FROM (
        SELECT fp.id AS filter_id, fp.para_id
        FROM filtered_paragraphs fp
        WHERE fp.id > :last AND fp.filter_name = :filter
        ORDER BY fp.id LIMIT :limit
    ) AS ft

    --Ignore previously processed ones.
    WHERE NOT EXISTS (
        SELECT 1 FROM extracted_materials em
        WHERE em.para_id = ft.para_id
        AND em.method_id = :mid
    );
    """

    t2 = log.info("Querying list of non-processed '{}' paragraphs.",
                  method.para_subset)

    records = postgres.raw_sql(
        query, filter=method.para_subset, mid=method.id, last=last,
        limit=args.limit)

    t2.note("Found {} paragraphs not processed.", len(records))

    if len(records) == 0:
        return
    else:
        log.info("Unprocessed Row IDs: {} to {}",
                 records[0].filter_id, records[-1].filter_id)

    # Initialize the LLM extractor.
    pipeline = LLMPipeline(db, method, sett.Run.directory,
                           sett.DataFiles.polymer_namelist_jsonl,
                           sett.DataFiles.properties_json)

    pipeline.init_shot_selector(
        sett.NERPipeline.model, sett.NERPipeline.pytorch_device, args.rebuild)

    n = 0
    new = 0
    processed_para = []

    log.info("Running LLM pipeline on '{}' filtered paragraphs.",
             method.para_subset)
    log.info("Extraction method = {}", method.name)
    log.info("Checkpoint info = {}", ckpt_info)


    # Process each paragraph.
    for row in tqdm(records):
        n += 1
        if row.filter_id < last:
            continue

        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            break

        # Fetch the paragraph.
        paragraph = PaperTexts().get_one(db, {'id': row.para_id})

        # Do not process the same paragraph again.
        if paragraph.id in processed_para:
            continue

        # Print the text if we are in debug mode.
        if sett.Run.debugCount > 0:
            print(paragraph.text)

        # Run the pipeline on the paragraph.
        t1 = log.trace("Running LLM Pipeline on paragraph {}", row.para_id)
        try:
            new += pipeline.run(paragraph)
            t1.done("LLM Pipeline finished.")
            processed_para.append(paragraph.id)
        except Exception as err:
            log.error("Failed to process paragraph {}: {}", row.para_id, err)
            if sett.Run.debugCount > 0: raise err
        
        log.info("Cumulative total new records: {}", new)

        last = row.filter_id
        if not (n % 50) or n == len(records):
            log.info("Processed {} paragraphs.", n)

    # Store the last processed id.
    log.note("Last processed row ID: {}", last)
    checkpoint.add_new(
        db, args.method, FilteredParagraphs.__tablename__, last, ckpt_info)

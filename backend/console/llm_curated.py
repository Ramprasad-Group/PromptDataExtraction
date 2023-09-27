import os
import pylogg
from argparse import ArgumentParser, _SubParsersAction

ScriptName = 'llm-curated'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Run LLM pipeline on curated data rows.')
    parser.add_argument(
        'runname',
        help="Name of the run, e.g., test-llm-pipeline.")
    parser.add_argument(
        '--prop', default=None,
        help="Name of the property, e.g., Tg, bandgap.")
    parser.add_argument(
        '--api', default='polyai',
        choices=['openai', 'polyai'],
        help="API endpoint, openai or polyai. Defaults to polyai.")
    parser.add_argument(
        '--rebuild', default=False,
        action='store_true',
        help="Rebuild the curated dataset and recompute the embeddings.")


def run(args: ArgumentParser):
    import openai
    from backend import postgres, sett
    from backend.postgres.orm import CuratedData, PaperTexts
    from backend.prompt_extraction.pipeline import LLMPipeline
    from backend.prompt_extraction.shot_selection import (
        RandomShotSelector, DiverseShotSelector
    )

    # Debugging
    # pylogg.setConsoleStack(show=True)
    # pylogg._conf.line_width = 150

    if args.api == 'openai':
        assert sett.LLMPipeline.openai_key is not None, \
            "openai_key is not set in the settings file."
        openai.api_key = sett.LLMPipeline.openai_key

    elif args.api == 'polyai':
        try:
            import polyai.api
        except:
            log.critical("Failed to import polyai, make sure it's installed.")
            exit(1)
        assert sett.LLMPipeline.polyai_key, \
            "polyai_key is not set in the settings file."
        polyai.api.api_key = sett.LLMPipeline.polyai_key

    db = postgres.connect()

    model = sett.LLMPipeline.openai_model \
        if args.api == 'openai' else sett.LLMPipeline.polyai_model

    extraction_info = {
        'prompt_id': 1 if args.prop else 0,
        'api': args.api,
        'model': model,
        'temperature': 0.001,
        'specific_property': args.prop,
        'shots': sett.LLMPipeline.n_shots,
        'shot_sampling': sett.LLMPipeline.shot_sampling,
        'max_api_retries': sett.LLMPipeline.max_api_retries,
        'api_retry_delay': sett.LLMPipeline.api_retry_delay,
        'api_request_delay': sett.LLMPipeline.api_request_delay,
        'method': 'llm-pipeline',
        'dataset': 'curated',
        'runname': args.runname,
        'user': sett.Run.userName,
    }

    log.info("Running LLM pipeline on curated dataset.")
    log.info("Extraction info = {}", extraction_info)

    # Initialize shot sampler.
    shot_curated_dataset = os.path.join(sett.Run.directory, "shots.json")
    shot_embeddings_file = os.path.join(sett.Run.directory, "embeddings.json")

    if sett.LLMPipeline.shot_sampling == 'random':
        shotselector = RandomShotSelector(
            min_records=sett.LLMPipeline.min_records_in_curated)
    
    elif sett.LLMPipeline.shot_sampling == 'diverse':
        shotselector = DiverseShotSelector(
            min_records=sett.LLMPipeline.min_records_in_curated)
    
    else:
        log.critical("Invalid shot_sampling: {}", sett.LLMPipeline.shot_sampling)
        raise ValueError("Invalid shot sampling.")

    # Load or build the curated dataset for shot selection.
    shotselector.build_curated_dataset(db, shot_curated_dataset, args.rebuild)

    # Load or calculate embeddings for the curated data texts.
    shotselector.compute_embeddings(
        sett.NERPipeline.model, sett.NERPipeline.pytorch_device,
        shot_embeddings_file, args.rebuild,
    )

    # Initialize the LLM extractor.
    pipeline = LLMPipeline(db,
        sett.DataFiles.polymer_namelist_jsonl, sett.DataFiles.properties_json,
        extraction_info, debug = sett.Run.debugCount > 0)
    pipeline.set_shot_selector(shotselector)

    n = 0
    new = 0
    processed_para = []

    # Process each paragraph linked to the curated data.
    for data in next(CuratedData().iter(db, size=100)):
        n += 1
        print(n, data.doi)

        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            break

        if data.para_id in processed_para:
            continue
        else:
            processed_para.append(data.para_id)

        paragraph = PaperTexts().get_one(db, {'id': data.para_id})

        if sett.Run.debugCount > 0:
            print(paragraph.text)

        # Run the pipeline on the paragraph.
        t1 = log.trace("Running LLM Pipeline on paragraph.")
        new += pipeline.run(paragraph)
        t1.info("LLM Pipeline finished. Cumulative total new records: {}", new)


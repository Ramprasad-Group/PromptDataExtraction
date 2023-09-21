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
        '--api', default='polyai',
        choices=['openai', 'polyai'],
        help="API endpoint, openai or polyai. Defaults to polyai.")
    parser.add_argument(
        '--prop', default='Tg',
        choices=['Tg', 'bandgap'],
        help="Property to process. Defaults to Tg.")


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

    model = sett.LLMPipeline.openai_model if args.api == 'openai' \
        else sett.LLMPipeline.polyai_model

    extraction_info = {
        'prompt_id': sett.LLMPipeline.prompt,
        'api': args.api,
        'model': model,
        'temperature': 0.001,
        'shots': sett.LLMPipeline.n_shots,
        'shot_sampling': sett.LLMPipeline.shot_sampling,
        'method': 'llm-pipeline',
        'dataset': 'curated',
        'runname': args.runname,
        'user': sett.Run.userName,
    }

    log.info("Running LLM pipeline on curated dataset.")
    log.info("Extraction info = {}", extraction_info)

    # Initialize the LLM extractor
    pipeline = LLMPipeline(db,
        sett.DataFiles.polymer_namelist_jsonl, sett.DataFiles.properties_json,
        extraction_info, debug = sett.Run.debugCount > 0)
    
    shotselector = RandomShotSelector(min_records=2)
    # shotselector = DiverseShotSelector(min_records=2)

    # Load or build the curated dataset for shot selection.
    shot_curated_dataset = os.path.join(
        sett.Run.directory, "curated_shot_data.json")    
    shotselector.build_curated_dataset(db, shot_curated_dataset)

    # Load or calculate embeddings for the curated data texts.
    shot_embeddings_file = os.path.join(
        sett.Run.directory, "curated_shot_embeddings.json")
    shotselector.compute_embeddings(
        sett.NERPipeline.model, sett.NERPipeline.pytorch_device,
        shot_embeddings_file
    )

    pipeline.set_shot_selector(shotselector)

    n = 0
    # Process each paragraph linked to the curated data.
    for data in next(CuratedData().iter(db, size=100)):
        n += 1
        print(n, data.doi)

        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            break

        paragraph = PaperTexts().get_one(db, {'id': data.para_id})

        if sett.Run.debugCount > 0:
            print(paragraph.text)

        # Run the pipeline on the paragraph.
        pipeline.run(paragraph)


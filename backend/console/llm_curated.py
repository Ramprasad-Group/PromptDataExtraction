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
    from backend.prompt_extraction.shot_selection import RandomShotSelector

    pylogg.setConsoleStack(show=True)
    pylogg._conf.line_width = 200

    if args.api == 'openai':
        assert sett.LLMPipeline.openai_key is not None
        openai.api_key = sett.LLMPipeline.openai_key

    elif args.api == 'polyai':
        try:
            import polyai.api
        except:
            log.critical("Failed to import polyai, make sure it's installed.")
            exit(1)
        assert sett.LLMPipeline.polyai_key
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
    }


    log.info("Running LLM pipeline on curated dataset.")
    log.info("Extraction info = {}", extraction_info)

    # Initialize the LLM extractor
    pipeline = LLMPipeline(db, sett.DataFiles.polymer_nen_json,
                           sett.DataFiles.properties_json, extraction_info,
                           debug = sett.Run.debugCount > 0)
    
    shotselector = RandomShotSelector(min_records=2)
    try:
        shotselector.load_curated_dataset("shot_data.json")
    except:
        shotselector.build_curated_dataset(db, criteria={})
        shotselector.save_curated_dataset("shot_data.json")

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

        pipeline.run(paragraph)


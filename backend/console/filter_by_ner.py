import pylogg
from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction
from backend.postgres.orm import FilteredParagraphs, PaperTexts

ScriptName = 'filter-by-ner'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Run NER pipeline on the ner-filtered paragraph rows.')
    parser.add_argument(
        "-r", "--filter", default='ner_filter',
        help="Optional name of the ner filter. Default: ner_filter")
    parser.add_argument(
        "-l", "--limit", default=100000, type=int,
        help="Number of paragraphs to process. Default: 100000")


def _add_to_filtered_paragrahs(db, para_id, ner_filter_name):
    paragraph = FilteredParagraphs().get_one(db, {
          'para_id': para_id, 'filter_name': ner_filter_name})

    if paragraph is not None:
        log.trace(f"Paragraph in PostGres: {para_id}. Skipped.")
        return False
    
    else:
        obj = FilteredParagraphs()
        obj.para_id = para_id
        obj.filter_name = ner_filter_name
        obj.insert(db)
        log.trace(f"Added to PostGres: {para_id}")


def _ner_filter(ner_tags, polymer_only = False) -> bool:
    """
    Return true if the NER tags contains all required entities
    needed for extraction.
    """

    polymer_entities = ['POLYMER', 'MONOMER', 'POLYMER_FAMILY']
    other_entities = ['ORGANIC', 'INORGANIC']

    value_ok = False
    material_ok = False
    property_ok = False

    for item in ner_tags:
        if item.label == 'PROP_VALUE':
            value_ok = True
        elif item.label == 'PROP_NAME':
            property_ok = True
        elif polymer_only and item.label in polymer_entities:
            material_ok = True
        elif not polymer_only \
            and item.label in polymer_entities + other_entities:
            material_ok = True

    return (value_ok and material_ok and property_ok)


def run(args: ArgumentParser):
    from backend import postgres, sett
    from backend.utils import checkpoint
    from backend.record_extraction import bert_model

    db = postgres.connect()

    runinfo = {
        'user': sett.Run.userName,
        'filter_by': 'material-property-value',
    }

    # Last processed row.
    last = checkpoint.get_last(
        db, args.filter, PaperTexts.__tablename__, runinfo)
    log.info("Last run row ID: {}", last)

    # Query the unprocessed list of rows.
    # This may take a while depending on the SQL.
    query = """
    SELECT pt.id AS para_id FROM paper_texts pt
    WHERE pt.id > :last ORDER BY pt.id LIMIT :limit;
    """

    t2 = log.info("Querying list of non-processed paragraphs.")
    records = postgres.raw_sql(query, {'last': last, 'limit': args.limit})
    t2.note("Found {} paragraphs not processed.", len(records))

    if len(records) == 0:
        return
    else:
        log.note(
            "Row IDs: {} to {}", records[0].para_id, records[-1].para_id)

    # Load Materials bert to GPU
    bert = bert_model.MaterialsBERT(sett.NERPipeline.model)
    bert.init_local_model(device=sett.NERPipeline.pytorch_device)

    log.info("Running NER filter on selected paragraphs.")
    log.info("Run info = {}", runinfo)

    n = 0
    p = 0
    # Process each paragraph linked to the curated data.
    for row in tqdm(records):
        n += 1
        if row.para_id < last:
            continue

        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            break

        # Fetch the paragraph.
        paragraph = PaperTexts().get_one(db, {'id': row.para_id})

        ner_tags = bert.get_tags(paragraph.text)

        if _ner_filter(ner_tags):
            log.trace("Para {} passed NER filter.", row.para_id)
            _add_to_filtered_paragrahs(db, row.para_id, args.filter)
            p += 1

            if not (p+1) % 50:
                log.note("NER filter passed: {} / {} paragraphs ({:.02f} %)",
                         p, n, 100 * p / n)
                db.commit()
        
        last = row.para_id

    log.note("NER filter passed: {} / {} paragraphs ({:.02f} %)",
             p, n, 100 * p / n)

    # Store the last processed id.
    log.note("Last processed row ID: {}", last)
    checkpoint.add_new(
        db, args.filter, PaperTexts.__tablename__, last, runinfo)

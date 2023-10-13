import pylogg
from tqdm import tqdm
from argparse import ArgumentParser, _SubParsersAction

ScriptName = 'token-count'

log = pylogg.New(ScriptName)


def add_args(subparsers: _SubParsersAction):
    parser: ArgumentParser = subparsers.add_parser(
        ScriptName,
        help='Calculate the number of tokens for the paragraphs defined by a specific method.')
    parser.add_argument(
        "-m", "--method", required=True,
        help="Name of the method from the extraction_methods table.")
    parser.add_argument(
        "-l", "--limit", default=10000000, type=int,
        help="Number of paragraphs to process. Default: 10000000")


def _num_tokens_from_string(string: str, model = "gpt-3.5-turbo") -> int:
    """Returns the number of tokens in a text string."""
    import tiktoken
    # encoding = tiktoken.get_encoding(encoding_name)
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def _update(n, new):
    log.info("0-shot input cost: $ {:.2f} ({:,} paras)", new/1000 * 0.0015, n)
    log.note("1-shot estimated total cost: $ {:.2f} ({:,} paras)",
             3.50 * new/1000 * 0.0015, n)


def run(args: ArgumentParser):
    from backend import postgres, sett
    from backend.postgres import persist, checkpoint
    from backend.postgres.orm import PaperTexts, FilteredParagraphs

    db = postgres.connect()

    method = persist.get_method(db, name=args.method)
    if method is None:
        log.critical("No such method defined in DB: {}", args.method)
        exit(1)

    log.info("Calculating number tokens using TikToken.")

    ckpt_info = {
        'user': sett.Run.userName,
        'method': method.name,
        'filter_name': method.para_subset,
    }

    # Last processed row.
    last = checkpoint.get_last(
        db, f"token_count-{method.name}", FilteredParagraphs.__tablename__,
        ckpt_info)
    log.info("Last run row ID: {}", last)

    query = """
    --Get the para ids of the filtered paragraphs.
    SELECT fp.id AS filter_id, fp.para_id
    FROM filtered_paragraphs fp
    WHERE fp.id > :last AND fp.filter_name = :filter
    ORDER BY fp.id LIMIT :limit;
    """

    t2 = log.info("Querying list of '{}' paragraphs.", method.para_subset)

    records = postgres.raw_sql(
        query, filter=method.para_subset, mid=method.id, last=last,
        limit=args.limit)

    t2.note("Found {:,} paragraphs.", len(records))

    if len(records) == 0:
        return
    else:
        log.info("Row IDs: {} to {}", records[0].filter_id,
                 records[-1].filter_id)

    n = 0
    new = 0

    # Process each paragraph.
    for row in tqdm(records):
        n += 1
        if row.filter_id < last:
            continue

        if sett.Run.debugCount > 0 and n > sett.Run.debugCount:
            break

        # Fetch the paragraph.
        paragraph : PaperTexts = PaperTexts().get_one(db, {'id': row.para_id})

        # Run the pipeline on the paragraph.
        new += _num_tokens_from_string(paragraph.text)

        last = row.filter_id
        if not (n % 1000):
            _update(n, new)

    log.note("Last processed row ID: {}", last)
    checkpoint.add_new(
        db, f"token_count-{method.name}", FilteredParagraphs.__tablename__,
        last, ckpt_info)
    _update(n, new)

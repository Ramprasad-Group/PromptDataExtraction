from dataclasses import dataclass, field
# from typing import Optional

from transformers import HfArgumentParser

@dataclass
class Arguments:
    """
    Arguments pertaining to what data we are going to input our model for training and eval.
    """
    use_debugpy: bool = field(
        default=False, metadata={"help": "Use remote debugging"}
    )

    debug: bool = field(
        default=False, metadata={"help": "Run code in debug mode wherein the run stops after debug_count documents are processed"}
    )

    delete_collection: bool = field(
        default=False, metadata={"help": "Delete collection if it exists"}
    )

    use_llm: bool = field(
        default=False, metadata={"help": "Run full text extraction code using OpenAI API"}
    )

    collection_output_name: str = field(
        default="full_text_data", metadata={"help": "Name of output collection"}
    )

    create_dataset: bool = field(
        default=False, metadata={"help": "Create dataset again even if present if this option is true"}
    )

    create_embeddings: bool = field(
        default=False, metadata={"help": "Create embeddings again even if present if this option is true"}
    )
    use_conventional_pipeline: bool = field(
        default=False, metadata={"help": "Create embeddings again even if present if this option is true"}
    )

    mode: str = field(
        default="Tg", metadata={"help": "mode can be Tg or bandgap"}
    )

    doi_error_list_file: str = field(
        default=None, metadata={"help": "Path to file where incorrectly predicted DOIs are stored"}
    )

    debug_count: int = field(
        default=10, metadata={"help": "Number of examples to run in debug mode"}
    )

    seed_count: int = field(
        default=1, metadata={"help": "Number of seed examples to run in debug mode"}
    )

    skip_n: int = field(
        default=0, metadata={"help": "Number of documents to skip when querying the database"}
    )

    prompt_index: int = field(
        default=0, metadata={"help": "Prompt to pick"}
    )

    seed_sampling: str = field(
        default="minimum", metadata={"help": "Seed sampling method. Can be random, minimum, baseline_diversity and error_diversity"}
    )

    experiment_name: str = field(
        default="test_run", metadata={"help": "Name of experiment"}
    )

    # dump_input: bool = field(
    #     default=False, metadata={"help": "Dump inputs to file and load from file if needed"}
    # )


def parse_args(args):
    parser = HfArgumentParser(Arguments)
    args = parser.parse_args_into_dataclasses(args=args)

    return args



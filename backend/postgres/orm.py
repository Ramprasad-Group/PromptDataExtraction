from datetime import datetime
from typing import Any, Optional, Dict, Literal

from backend.postgres import ORMBase
from sqlalchemy import Text, JSON, ForeignKey, Integer, DateTime, Float, ARRAY, VARCHAR, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Papers(ORMBase):
    """
    PostGres table containing summary information about a paper including
    DOI, directory, title, abstract etc.
    Additional summary columns can be included later if needed.

    Attributes:
        doi:        DOI string of the paper.

        publisher:  Full name of the publisher, see also `directory`.

        title:      Title of the paper..

        abstract:   Abstract of the paper.

        doctype:     One of xml, html. (planned: pdf, txt etc.)

        directory:  Directory name in corpus where the file can be found.

    """
    __tablename__ = "papers"

    doi: Mapped[str] = mapped_column(Text, unique=True)
    publisher: Mapped[str] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    doctype: Mapped[str] = mapped_column(VARCHAR(length=6))
    directory: Mapped[str] = mapped_column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FilteredPapers(ORMBase):
    """
    PostGres table to store the list of DOIs that passed a named filter,
    for example the polymer filter.

    Attributes:
        doi:            Formatted doi string that passed the filter.

        filter_name:    Filter name.

        filter_desc:    Filter description/comment, how the filtering was done.

    """

    __tablename__ = "filtered_papers"

    doi: Mapped[str] = mapped_column(Text, index=True)
    filter_name: Mapped[str] = mapped_column(Text)
    filter_desc: Mapped[str] = mapped_column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PaperTexts(ORMBase):
    """
    PostGres table containing newly parsed paper full texts paragraphs
    (not migrated from Mongodb) using the `backend.parser` module.

    Attributes:

        pid:        ID ForeignKey from the papers table.

        doi:        Formatted doi string.

        doctype:    html or xml (extension of the original file).

        section:    [Optional] Section name if parsed from the paper.
                    (Example: abstract, introduction etc.)

        tag:        [Optional] Tag/selector used to parse the text.
                    (Example: p, span etc.)

        text:       Actual text content of the paragraph.

        directory:  Directory containing the file in corpus (not publisher).

    """

    __tablename__ = "paper_texts"

    pid: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete='CASCADE'),
                        unique=False, index=True)

    doi: Mapped[str] = mapped_column(Text, index=True)
    doctype: Mapped[str] = mapped_column(VARCHAR(length=6))
    section: Mapped[str] = mapped_column(Text, nullable=True)
    tag: Mapped[str] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    directory: Mapped[str] = mapped_column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FilteredTexts(ORMBase):
    """
    PostGres table to store the id of the rows in `paper_texts` that passed
    a named filter, for example the NER or Tg filter.

    Attributes:
        para_id:    Foreign key referencing the source paragraph checked against
                    the filter.

        filter_name:    Filter name.

        filter_desc:    Filter description/comment, how the filtering was done.

    """

    __tablename__ = "filtered_texts"

    para_id: Mapped[int] = mapped_column(
        ForeignKey("paper_texts.id", ondelete='CASCADE'),
        unique=False, index=True)
    
    filter_name: Mapped[str] = mapped_column(Text, index=True)
    filter_desc: Mapped[str] = mapped_column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PaperData(ORMBase):
    """
    PostGres table to store data extracted from a paragraph using
    the NER or LLM pipeline for each property.

    Attributes:
        para_id:    Foreign key referencing the source paragraph used to extract
                    the data.

        doi:        DOI string of the paper.

        property:   Name of the property.

        material:   Name of the material/polymer.

        value:      Extracted value for the property.

        unit:       Extracted unit for the property.

        condition:  (dict) Additional conditions/information about the
                    extracteddata.

        smiles:     [Optional] SMILES string for the polymer/material if
                    available.

        extraction_method:
                    Name of the extraction method, (example: bert,
                    openai, polyai etc.)

        extraction_model:
                    Name of the extraction model, (example: materials bert,
                    gpt-3.5-turbo, vicuna-33B etc.)

    """
    __tablename__ = "paper_data"

    para_id: Mapped[int] = mapped_column(
        ForeignKey("paper_texts.id", ondelete='CASCADE'),
        unique=False, index=True)

    doi: Mapped[str] = mapped_column(Text, index=True)
    property: Mapped[str] = mapped_column(Text, index=True)

    material: Mapped[str] = mapped_column(Text)
    value : Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(Text, nullable=True)

    condition: Mapped[Dict] = mapped_column(JSON, default={})
    smiles: Mapped[str] = mapped_column(Text, nullable=True)

    extraction_method: Mapped[str] = mapped_column(Text)
    extraction_model: Mapped[str] = mapped_column(Text, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Polymers(ORMBase):
    """
    PostGres table containing known polymers, types, SMILES etc.
    (Migrated from https://github.com/Ramprasad-Group/polymer_scholar/blob/master/data/normalized_polymer_dictionary.json)

    Attributes:

        name:       Name of the polymer.

        is_norm:    True of the name is normalized.

        norm_id:    ID of the row containing the normalized name if name is not
                    normalized. NULL if already normalized.

        is_polymer: True if the material is a polymer.

        norm_name:  Normalized name.

        iupac_name: IUPAC name of the polymer if available.

        SMILES:     SMILES string of the polymer if available.

        is_family_name:
                    True if the name is a type of polymer family.

        is_copolymer:
                    True if the polymer is a copolymer.

        is_blend:   True if the polymer is a blend.

        is_composite:
                    True if the material is a composite.

        comments:   (dict) Comments about the polymer.

        details:    (dict) Additional details about the polymer.

    """
    __tablename__ = "polymers"

    # for all entities
    name : Mapped[str] = mapped_column(Text, index=True)
    is_norm : Mapped[bool] = mapped_column(Boolean, default=False)
    norm_id : Mapped[int] = mapped_column(Integer, nullable=True)

    # for normalized ones
    is_polymer : Mapped[bool] = mapped_column(Boolean, default=True)
    norm_name : Mapped[str] = mapped_column(Text, nullable=True)
    iupac_name : Mapped[str] = mapped_column(Text, nullable=True)
    smiles : Mapped[str] = mapped_column(Text, nullable=True)
    is_family_name : Mapped[bool] = mapped_column(Boolean, default=False)
    is_copolymer : Mapped[bool] = mapped_column(Boolean, default=False)
    is_blend : Mapped[bool] = mapped_column(Boolean, default=False)
    is_composite : Mapped[bool] = mapped_column(Boolean, default=False)
    comments: Mapped[Dict] = mapped_column(JSON, default={})
    details: Mapped[Dict] = mapped_column(JSON, default={})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class APIRequests(ORMBase):
    """
    PostGres table to store API requests and responses.

    Attributes:

        api:        Type of the API endpoint, eg. openai, polyai (string).

        model:      Model used to query eg. gpt-3.5-turbo (string).

        request:    Brief request string.

        response:   Brief response string.
        
        status:     Success, fail, too long etc. (string)
       
        para_id:    Foreign key referencing the source paragraph used to make
                    the api request.

        details:    Additional details about the interaction, eg. number of
                    shots, comments etc. (dict)

        request_obj:
                    The full request object sent to the api endpoint (dict)

        response_obj:
                    The full response object received from the
                    api endpoint. (dict)

        request_tokens:
                    Cost or the number of tokens used for request / cost. (int)

        response_tokens:
                    Cost or the number of tokens used for response / cost. (int)

    """

    __tablename__ = "api_requests"

    model: Mapped[str] = mapped_column(Text)
    api: Mapped[str] = mapped_column(Text)
    request: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Dict] = mapped_column(JSON)

    para_id: Mapped[int] = mapped_column(
            ForeignKey("paper_texts.id", ondelete='CASCADE'),
            unique=False, index=True)

    request_obj: Mapped[Dict] = mapped_column(JSON)
    response_obj: Mapped[Dict] = mapped_column(JSON)
    request_tokens: Mapped[int] = mapped_column(Integer, default=-1)
    response_tokens: Mapped[int] = mapped_column(Integer, default=-1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PaperSections(ORMBase):
    """
    [Deprecated: superseded by the `paper_texts` table.]
    PostGres table containing paragraph texts migrated from Mongodb parsed
    by Pranav. Some paragraphs were not migrated correctly due to inconsistent
    formats of the mongodb data.

    Attributes:
        doi:        DOI string of the paper.

        format:     One of xml, html.

        type:       Section type (h2, p etc.)

        name:       Section name (Introduction, Methods etc.)

        text:       Paragraph full text.
    
    """
    __tablename__ = "paper_sections"

    pid: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete='CASCADE'),
                        unique=False, index=True)

    doi: Mapped[str] = mapped_column(Text, index=True)
    format: Mapped[str] = mapped_column(VARCHAR(length=4))
    type: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PaperTables(ORMBase):
    __tablename__ = "paper_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    caption: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    downloaded: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    number: Mapped[Optional[str]] = mapped_column(Text)
    tbl_header: Mapped[Optional[str]] = mapped_column(Text)
    tbl_index: Mapped[Optional[str]] = mapped_column(Text)
    body: Mapped[Optional[str]] = mapped_column(Text)
    jsonl: Mapped[Optional[str]] = mapped_column(Text)
    descriptions: Mapped[Optional[ARRAY]] = mapped_column(ARRAY(Text, dimensions=1))

    pid: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete='CASCADE'),
                        unique=False, index=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.date_added is None:
            self.date_added = datetime.now()


class TableMeta(ORMBase):
    __tablename__ = "table_meta"

    table : Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    codeversion: Mapped[str] = mapped_column(Text, nullable=True)
    tag: Mapped[str] = mapped_column(Text, nullable=True)

    def __init__(self, table, **kwargs):
        super().__init__(**kwargs)
        self.table = table.__tablename__
        print("Table:", self.table)


if __name__ == "__main__":
    import sett
    from backend import postgres

    sett.load_settings()
    postgres.load_settings()

    # Create all tables if not already created
    ORMBase.metadata.create_all(postgres.engine())
    print("Done!")

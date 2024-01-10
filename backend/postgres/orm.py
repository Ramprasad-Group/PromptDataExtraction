from datetime import datetime
from typing import Any, Optional, Dict, Literal, List

from backend.postgres.base import ORMBase
from sqlalchemy import (
    Text, JSON, ForeignKey, Integer, DateTime, Float,
    ARRAY, VARCHAR, Boolean, String
)
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

    doi: Mapped[str] = mapped_column(Text, unique=True, index=True)
    publisher: Mapped[str] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    doctype: Mapped[str] = mapped_column(VARCHAR(length=6))
    directory: Mapped[str] = mapped_column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)



class PaperCorpus(ORMBase):
    """
    PostGres table containing list of all files found in the corpus.

    Attributes:

        doi:        DOI string of the paper.

        directory:  Directory name in corpus where the file can be found.

        doctype:    One of xml, html. (planned: pdf, txt etc.)

        filename:   Basename of the file.

        filebytes:  Size of file in bytes.

        filemtime:  Last modification time of the file reported by Linux.

    """

    __tablename__ = "paper_corpus"

    doi: Mapped[str] = mapped_column(Text, index=True)
    relpath: Mapped[str] = mapped_column(Text, unique=True, index=True)
    directory: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    doctype: Mapped[str] = mapped_column(VARCHAR(length=6))
    filebytes: Mapped[int] = mapped_column(Integer, default=-1)
    filemtime: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                nullable=True)

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


class TableCursor(ORMBase):
    """
    Postgres table to keep track of last processed row.

    Attributes:
        name:       Name of the process/filter.
        table:      Name of the table processed.
        row:        Last processed row number.
        description:
                    Optional comment or description.
    """
    __tablename__ = "table_cursor"

    name : Mapped[str] = mapped_column(Text)
    table : Mapped[str] = mapped_column(Text)
    row: Mapped[int] = mapped_column(Integer)
    comments: Mapped[Dict] = mapped_column(JSON, default={})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ExtractionMethods(ORMBase):
    """
    Postgres table to keep track of methods used to extract data.

    Attributes:
        name:       Name of the extraction method.

        dataset:    Name of the extracted dataset.

        model:      Model used for the extraction.

        api:        (Optional) API name.

        para_subset:
                    (Optional) Filter name of the sub dataset if any.

        info:       (Optional) Additional info about api, model, username etc.

    """

    __tablename__ = "extraction_methods"

    name : Mapped[str] = mapped_column(Text, unique=True)
    dataset : Mapped[str] = mapped_column(Text)
    model : Mapped[str] = mapped_column(Text)
    api : Mapped[str] = mapped_column(Text, nullable=True)
    para_subset : Mapped[str] = mapped_column(Text, nullable=True)
    extraction_info: Mapped[Dict] = mapped_column(JSON, default={})


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


ParagraphFilters = Literal['property_tg', 'property_td', 'property_tm',
                           'property_thermal_conductivity', 'NER']

class FilteredParagraphs(ORMBase):
    '''
    Table to track of the paragraphs passing a particular filter.

    Attributes:
        para_id:        Foreign key referencing to the paragraph from
                        paper_texts.

        filter_name:    Must be one of `ParagraphFilters`.
    '''

    __tablename__ = "filtered_paragraphs"

    para_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("paper_texts.id"), nullable= False,
        unique=False, index=True,
    )
    filter_name : Mapped[ParagraphFilters] = mapped_column(String)

    def __init__(self, **kw):
        super().__init__(**kw)


class ExtractedMaterials(ORMBase):
    """
    Table to store the material entities extracted from MaterialsBERT.

    Attributes:
        para_id:    Foreign key referencing the source paragraph checked against the filter.
        entity_name:
        materials_class
        polymer_type
        normalized_material_name
        coreferents
        components
        additional_info
        extraction_info
    """

    __tablename__ = "extracted_materials"

    para_id: Mapped[int] = mapped_column(
        ForeignKey("paper_texts.id", ondelete='CASCADE'),
        unique=False, index=True)
    
    method_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_methods.id",
                   ondelete='CASCADE', onupdate='CASCADE'),
                   unique=False, index=True)

    entity_name: Mapped[str] = mapped_column(Text)
    material_class: Mapped[str] = mapped_column(Text)
    polymer_type: Mapped[str] = mapped_column(Text)
    normalized_material_name: Mapped[str] = mapped_column(Text)
    coreferents: Mapped[List[str]] = mapped_column(ARRAY(String))
    components: Mapped[List[str]] = mapped_column(ARRAY(String))
    additional_info: Mapped[Dict] = mapped_column(JSON, default={})
    extraction_info: Mapped[Dict] = mapped_column(JSON, default={})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ExtractedAmount(ORMBase):
    '''
    Table to store the material amount corresponding to an entity if available

    Attributes:
        material_amount
        extraction_info
    '''

    __tablename__ = "extracted_material_amounts"

    para_id: Mapped[int] = mapped_column(
        ForeignKey("paper_texts.id", ondelete='CASCADE'),
        unique=False, index=True)

    method_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_methods.id",
                   ondelete='CASCADE', onupdate='CASCADE'),
                   unique=False, index=True)

    entity_name: Mapped[str] = mapped_column(Text)
    material_amount: Mapped[str] = mapped_column(Text)
    extraction_info: Mapped[Dict] = mapped_column(JSON, default={})

    def __init__(self, **kw):
        super().__init__(**kw)


class ExtractedProperties(ORMBase):
    '''
    Table to store the properties extracted from MaterialsBERT

    Attributes:
        material_id: Foreign key referencing to material entity
        entity_name: name of property
        value: str containing property value and units
        coreferents: list 
        numeric_value: numeric part of reported value, average if range 
        numeric_error: error reported for value
        value_average: boolean representing if reported property value is numeric or a range
        value_descriptor: condition given for reported value (ex: "less than" 8 eV)
        unit: property unit
        conditions: temperature_condition, frequency_condition
        extraction_info: dictionary containing extraction method, source set etc.

    '''
    
    __tablename__ = "extracted_properties"

    material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extracted_materials.id"), nullable= False
    )

    method_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_methods.id",
                   ondelete='CASCADE', onupdate='CASCADE'),
                   unique=False, index=True)

    entity_name: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    coreferents: Mapped[List[str]] = mapped_column(ARRAY(String))
    numeric_value: Mapped[float] = mapped_column(Float)
    numeric_error: Mapped[float] = mapped_column(Float, nullable=True)
    value_average: Mapped[bool] = mapped_column(Boolean, default=False)
    value_descriptor: Mapped[str] = mapped_column(Text, nullable=True)
    unit: Mapped[str]= mapped_column(Text, nullable=True)
    conditions: Mapped[Dict] = mapped_column(JSON, default={})
    extraction_info: Mapped[Dict] = mapped_column(JSON, default={})

    api_req: Mapped[int] = mapped_column(
        ForeignKey("api_requests.id", ondelete="SET NULL", onupdate='CASCADE'),
        nullable=True, unique=False, default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class RelMaterialProperties(ORMBase):
    '''
    Table to store many-to-many relationships of materials and 
    properties. This is necessary because the NER pipeline can provide
    multiple materials for the same properties and vice-versa.

    Attributes:
        material_id: Foreign key referencing material entity.
        property_id: Foreign key referencing property entity.
    '''
    __tablename__ = "rel_material_properties"

    material_id: Mapped[int] = mapped_column(
        ForeignKey("extracted_materials.id", ondelete='CASCADE',
                   onupdate='CASCADE'), unique=False, index=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("extracted_properties.id", ondelete='CASCADE',
                   onupdate='CASCADE'), unique=False, index=True)

    method_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_methods.id", ondelete='CASCADE',
                   onupdate='CASCADE'), unique=False, index=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ExtractedCrossrefs(ORMBase):
    '''
    Table to store the cross-references, synonyms, abbreviations etc.

    Attributes:
        name :      Name of the reference (e.g., abbr.)

        othername:  Other name of the reference (e.g., full form)

        reftype:    Cross-reference type (e.g., abbreviation, citation etc.)

    '''

    __tablename__ = "extracted_crossrefs"

    para_id: Mapped[int] = mapped_column(ForeignKey("paper_texts.id"),
        unique=False, index=True)

    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"),
        unique=False, index=True)
    
    name: Mapped[str] = mapped_column(Text, index=True)
    othername: Mapped[str] = mapped_column(Text)
    reftype: Mapped[str] = mapped_column(Text)

    def __init__(self, **kw):
        super().__init__(**kw)


class FilteredData(ORMBase):
    '''
    Table to track the extracted property, materials and paragraphs passing
    specific filters.

    Attributes:
        table_name:     Name of the table filter acted on.
                        Ex. extracted_properties, extracted_materials etc.
        table_row:      ID of the row in the target table.
        filter_on:      Name of the data group, e.g., Tg, bandgap, PS, PMMA.
        filter_name:    Name of the passed filter, e.g. valid_name.
    '''

    __tablename__ = "filtered_data"

    table_name  : Mapped[str] = mapped_column(String)
    table_row   : Mapped[int] = mapped_column(
        Integer, nullable= False, unique=False, index=True,
    )
    filter_on   : Mapped[str] = mapped_column(String, index=True)
    filter_name : Mapped[str] = mapped_column(String)

    def __init__(self, **kw):
        super().__init__(**kw)


class ExtractedData(ORMBase):
    '''
    Table for the finally exported/extracted data.

    Attributes:
        property_id:    ForeignKey referencing the extracted_properties row.
        method:         Name of the extraction method.
        material:       Name of the material.
        property:       Name of the property.
        value:          Numeric value of the property.
        unit:           Unit of the property value.
        doi:            DOI of the source paper.
        confidence:     Confidence score expressed as percentage (0-100).
    '''

    __tablename__ = "extracted_data"

    property_id: Mapped[int] = mapped_column(
        Integer,ForeignKey("extracted_properties.id", ondelete='CASCADE',
                           onupdate='CASCADE'), unique=True, index=True)
    method : Mapped[str] = mapped_column(String, index=True)
    material : Mapped[str] = mapped_column(String, index=True)
    property : Mapped[str] = mapped_column(String, index=True)
    value: Mapped[float] = mapped_column(Float)
    unit : Mapped[str] = mapped_column(String, nullable=True)
    doi : Mapped[str] = mapped_column(String, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0)

    def __init__(self, **kw):
        super().__init__(**kw)


PropertyScale = Literal['log', 'normal']

class PropertyMetadata(ORMBase):
    '''
    Table to store the metadata

    Attributes:
        name: name of property
        property: property identifier
        other_names: list of property names that can be reported in literature
        units: list of different units that can be seen in literature
        scale: Must be 'log' or 'normal'
        short_name: short name or symbol for the property name
        lower_limit: lower limit of range of values that can be seen
        upper_limit: upper limit of range of values that can be seen
    '''

    __tablename__ = "property_metadata"

    name: Mapped[str] = mapped_column(Text)
    property: Mapped[str] = mapped_column(Text)
    stdunit: Mapped[str] = mapped_column(VARCHAR)
    other_names: Mapped[List[str]] = mapped_column(ARRAY(String))
    units: Mapped[List[str]] = mapped_column(ARRAY(String))
    scale: Mapped[PropertyScale] = mapped_column(String, default='normal')
    short_name: Mapped[str]= mapped_column(Text, nullable=True)
    lower_limit: Mapped[Float]= mapped_column(Float, nullable=True)
    upper_limit: Mapped[Float]= mapped_column(Float, nullable=True)

    def __init__(self, **kw):
        super().__init__(**kw)


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

        method_id:  Foreign key referencing the method definition used to make
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
    response: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Dict] = mapped_column(JSON, default={})

    para_id: Mapped[int] = mapped_column(ForeignKey("paper_texts.id"),
            unique=False, index=True)

    method_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_methods.id", ondelete='CASCADE',
                   onupdate='CASCADE'), unique=False, index=True)

    request_obj: Mapped[Dict] = mapped_column(JSON)
    response_obj: Mapped[Dict] = mapped_column(JSON, nullable=True)
    request_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    response_tokens: Mapped[int] = mapped_column(Integer, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CuratedData(ORMBase):
    """
    PostGres table containing curated ground truth data.

    Attributes:

        para_id:    Foreign key referencing the source paragraph in paper_texts.

        doi:        DOI string of the paper.

        material:   Name of the material.

        property_name:
                    Name of the property.

        property_value:
                    String representing numerical value and unit for
                    the property.

        material_coreferents:
                    List of material other names.

        conditions:
                    Measurement or environment conditions about the data.

    """

    __tablename__ = "curated_data"

    para_id: Mapped[int] = mapped_column(
        ForeignKey("paper_texts.id"), unique=False, index=True)

    doi: Mapped[str] = mapped_column(Text, index=True)
    material: Mapped[str] = mapped_column(Text)
    property_name: Mapped[str] = mapped_column(Text)
    property_value: Mapped[str] = mapped_column(Text)
    material_coreferents: Mapped[List[str]] = mapped_column(ARRAY(String))
    conditions: Mapped[str] = mapped_column(Text, nullable=True)

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


if __name__ == "__main__":
    from backend import postgres, sett

    sett.load_settings()
    postgres.load_settings()

    # Create all tables if not already created
    ORMBase.metadata.create_all(postgres.engine())
    print("Done!")

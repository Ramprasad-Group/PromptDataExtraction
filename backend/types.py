from dataclasses import dataclass

@dataclass
class NerTag:
    """
    NER Tag object.
    
    Attributes:
        text    : The original text
        label   : The named entity
    """
    text : str
    label : str


@dataclass
class NerLabelGroup:
    """
    Joined NER tag object that combines consecutive tags.

    text    : The original text
    label   : The name of the entity
    start   : Start index of the entity
    end     : End index of the entity
    """
    text : str
    label : str
    start : int
    end : int 


@dataclass
class Property:
    """
    Property object.

    Attributes:
        value    : The numerical value
        unit     : The unit
        text     : Text representation
        error    : Standard error if any
        relation : Any relationship of the value, eg. <, >, ~ etc.
    """
    value : float
    unit : str
    text : str
    error : float
    relation : str

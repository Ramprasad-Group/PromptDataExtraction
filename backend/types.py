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
        name     : The property name
        value    : The numerical value
        unit     : The unit
        text     : The original text of the property value and unit
        error    : Standard error if any
        relation : Any relationship of the value, eg. <, >, ~ etc.
    """
    name : str
    value : float
    unit : str
    text : str
    error : float
    relation : str


@dataclass
class Record:
    """
    A material record that has been extracted from text.

    Attributes:
        name        : The material name
        property    : A Property object
    """
    material : str
    property : Property = None

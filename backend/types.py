from dataclasses import dataclass

@dataclass
class NerTag:
    """ NER Tag object.
    Attributes:
        text    (str): The original text
        label   (str): The named entity
    """
    text : str
    label : str


@dataclass
class NerLabelGroup:
    """
    Joined NER tag object that combines consecutive tags.

    text    (str): The original text
    label   (str): The name of the entity
    start   (int): Start index of the entity
    end     (int): End index of the entity
    """
    text : str
    label : str
    start : int
    end : int 

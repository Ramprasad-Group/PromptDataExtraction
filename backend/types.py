from dataclasses import dataclass, field

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
class Material:
    """
    Material object.

    Attributes:
        name    : The name of the material
        tag     : The type of material (NER tag)
        coreferents :   The list of coreferents for the material
    """
    name : str
    tag : str
    coreferents : list[str]


@dataclass
class Polymer(Material):
    """
    Polymer object.

    Attributes:
        name    : The name of the polymer
        tag     : The type of polymer  (NER tag)
        coreferents :   The list of coreferents for the polymer
        is_homopolymer  :   True if homopolymer
        is_copolymer    :   True if copolymer
        is_starpolymer  :   True if starpolymer
    """
    is_homopolymer  : bool = False
    is_copolymer    : bool = False
    is_starpolymer  : bool = False



@dataclass
class Property:
    """
    Property object.

    Attributes:
        name     : The property name
        value    : The numerical value
        unit     : The unit
        text     : The original text of the property value and unit
        tag      : The type of property  (NER tag)
        coreferents :   The list of coreferents for the property
        error    : Standard error if any
        relation : Any relationship of the value, eg. <, >, ~ etc.
    """
    name : str = None
    value : float = None
    unit : str = None
    text : str = None
    tag  : str = None
    coreferents : list[str] = field(default_factory=lambda: [])
    error : float = None
    relation : str = None


@dataclass
class Record:
    """
    A material record that has been extracted from text.

    Attributes:
        material    : A Material object
        property    : A Property object
    """
    material : Material | Polymer = None
    property : Property = None

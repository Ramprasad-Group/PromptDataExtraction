from .acs import ACSParser
from .elsevier import ElsevierParser
from .wiley import WileyParser
from .nature import NatureParser
from .springer import SpringerParser
from .iop import IOPParser
from .aip import AIPParser
from .ecs import ECSParser
from .hindawi import HindawiParser
from .informa import InformaParser
from .rsc import RSCParser
from .document import DocumentParser


def PaperParser(publisher, filepath) -> DocumentParser:
    """ Return an appropriate document parser based on it's publisher. 
    
    Parameters:
        publisher   string: Name of the publisher.
        filepath    string: Path to the XML or HTML document.

    Returns:
        None if no such publisher.
    """
    parsers = {
        'acs': ACSParser,
        'aip': AIPParser,
        'ecs': ECSParser,
        'elsevier': ElsevierParser,
        'hindawi': HindawiParser,
        'informa_uk': InformaParser,
        'iop_publishing': IOPParser,
        'nature': NatureParser,
        'rsc': RSCParser,
        'springer': SpringerParser,
        'wiley': WileyParser
    }

    if publisher not in parsers.keys():
        return None

    return parsers[publisher](filepath)

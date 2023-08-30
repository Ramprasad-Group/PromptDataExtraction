from backend.nlp import ner
from backend.types import NerLabelGroup

class TextDataExtractor:
    """
    Handle the NER pipeline. Given a text and the list of NER tags,
    extract the data from the text using the tags.

    """
    def __init__(self, text : str, tags : list, debug=False) -> None:
        # The tags are calculated by the MaterialsBERT model seperately since,
        # the BERT model is expensive to recreate.
        self.text = text
        self.tags = tags
        self.debug = debug
        self.polymers : list[str] = []
        self.materials : list[str] = []
        self.properties : list[str] = []
        self.abbreviations : list[str] = []

    def _identify_entities(self, groups : list[NerLabelGroup]):
        self.polymers = [g.text for g in groups
                          if g.label in ner.PolymerLabels]
        self.materials = [g.text for g in groups
                          if g.label in ner.ChemicalLabels]
        self.properties = [g.text for g in groups if g.label == 'PROP_NAME']
        self.abbreviations = ner.find_chemdata_abbr(self.text)
        

    def extract(self, only_polymers=False) -> list:
        """ Run data extraction pipeline. """
        if not ner.check_relevant_ners(self.tags, only_polymers) \
            and not self.debug:
                return []

        # Combine consecute NER tags.
        groups = ner.group_consecutive_tags(self.tags)

        # Identify the materials, properties and abbreviations from the tags.
        self._identify_entities(groups)

        # Parse material names.

        # Parse property names.

        # Parse property values (records).

        return groups

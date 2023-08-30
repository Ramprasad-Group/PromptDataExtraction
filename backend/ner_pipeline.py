from backend.nlp import ner
from backend.nlp import materials
from backend.nlp import properties
from backend.nlp import records
from backend.types import NerLabelGroup


class TextDataExtractor:
    """
    Handle the NER pipeline: given a text and the list of NER tags,
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
        """ Idenfity the polymers, materials, properties and abbreviations
            mentioned in the text using the NER tags.
        """
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
        mat = materials.MaterialEntities(self.tags, self.text, self.materials, self.abbreviations)
        mat.run()

        # Parse property names.
        prop = properties.PropertyExtractor(self.tags, self.text, self.properties, self.abbreviations)
        prop.run()

        # Parse property values (records).
        rec = records.MaterialAmountExtractor(self.tags)
        rec.run()

        # Combine the parsed materials, properties and values.

        return groups

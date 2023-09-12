from backend.nlp import ner
from backend.nlp import materials
from backend.nlp import properties
from backend.nlp import records
from backend.types import NerLabelGroup, Material, Polymer, Property


class TextDataExtractor:
    """
    Handle the NER pipeline: given a text and the list of NER tags,
    extract the data from the text using the tags.

    """
    def __init__(self, text : str, tags : list, only_polymers = False) -> None:
        # The tags are calculated by the MaterialsBERT model seperately since,
        # the BERT model is expensive to recreate.
        self.text = text
        self.tags = tags
        self.only_polymers = only_polymers
        self.polymers : list[str] = []
        self.materials : list[str] = []
        self.properties : list[str] = []
        self.abbreviations : list[str] = []


    def _identify_entities(self, groups : list[NerLabelGroup]):
        """ Idenfity the polymers, materials, properties and abbreviations
            mentioned in the text using the NER tags.
        """

        for g in groups:
            if g.label in ner.PolymerLabels:
                item = Polymer(name=g.text, tag=g.label, coreferents=[g.text])
                self.polymers.append(item)
                self.materials.append(item)

            elif g.label in ner.ChemicalLabels:
                item = Material(name=g.text, tag=g.label, coreferents=[g.text])
                self.materials.append(item)

            elif g.label == 'PROP_NAME':
                item = Property(name=g.text, text=g.text, coreferents=[g.text],
                                tag=g.label)
                self.properties.append(item)

        self.abbreviations = ner.find_chemdata_abbr(self.text)


    def check_relevant_ners(self) -> bool:
        """ Return True if all of name, property and values are available
            in the predicted NER tags.
        """
        criteria = [
            'PROP_VALUE' in [item.label for item in self.tags],
            'PROP_NAME'  in [item.label for item in self.tags],
            any([
                any([
                    self.only_polymers
                    and item.label in ner.PolymerLabels
                    for item in self.tags
                ]),
                any([
                    not self.only_polymers
                    and item.label in ner.PolymerLabels + ner.ChemicalLabels
                    for item in self.tags
                ]),
            ])
        ]

        return all(criteria)


    def extract(self, debug : bool = False) -> list:
        """ Run data extraction pipeline. """
        if not self.check_relevant_ners() and not debug:
            return []

        # Combine consecute NER tags.
        groups = ner.group_consecutive_tags(self.tags)

        # Identify the materials, properties and abbreviations from the tags.
        self._identify_entities(groups)

        # Parse material names.
        mat = materials.MaterialEntities(self.tags, self.text, self.materials, self.abbreviations)
        return mat
        # mat.run()

        # # Parse property names.
        # prop = properties.PropertyExtractor(self.tags, self.text, self.properties, self.abbreviations)
        # prop.run()

        # # Parse property values (records).
        # rec = records.MaterialAmountExtractor(self.tags)
        # rec.run()

        # # Combine the parsed materials, properties and values.

        # return groups


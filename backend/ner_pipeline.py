from backend.nlp import ner

class TextDataExtractor:
    def __init__(self, text : str, tags : list, debug=False) -> None:
        self.text = text
        self.tags = tags
        self.debug = debug
        self.polymers : list[str] = []
        self.materials : list[str] = []
        self.properties : list[str] = []
        self.abbreviations : list[str] = []


    def extract(self, only_polymers=False) -> list:
        if not ner.check_relevant_ners(self.tags, only_polymers) \
            and not self.debug:
                return []

        # continue with extraction
        groups = ner.group_consecutive_tags(self.tags)
        self.materials = [g.text for g in groups
                          if g.label in ner.PolymerLabels]
        self.materials = [g.text for g in groups
                          if g.label in ner.ChemicalLabels]
        self.properties = [g.text for g in groups if g.label == 'PROP_NAME']

        self.abbreviations = ner.find_chemdata_abbr(self.text)

        return groups



from backend import types
from chemdataextractor.doc import Paragraph

PolymerLabels = ['POLYMER', 'MONOMER', 'POLYMER_FAMILY']
ChemicalLabels = ['ORGANIC', 'INORGANIC']

class RecordExtractor:
    def __init__(self, text : str, tags : list, debug=False) -> None:
        self.text = text
        self.tags = tags
        self.debug = debug
        self.polymers : list[str] = []
        self.materials : list[str] = []
        self.properties : list[str] = []
        self.abbreviations : list[str] = []


    def extract(self, only_polymers=False) -> list:
        if not self._check_relevance(only_polymers) and not self.debug:
            return []

        # continue with extraction
        groups = self._group_consecutive_tags()        
        self.materials = [g.text for g in groups if g.label in PolymerLabels]
        self.materials = [g.text for g in groups if g.label in ChemicalLabels]
        self.properties = [g.text for g in groups if g.label == 'PROP_NAME']

        # self.abbreviations = self._find_chemdata_abbr(self.text)

        return groups

        
    def _check_relevance(self, only_polymers : bool) -> bool:
        """ Check if the text has name, property and values in it. """
        criteria = [
            'PROP_VALUE' in [item.label for item in self.tags],
            'PROP_NAME'  in [item.label for item in self.tags],
            any([
                any([
                    only_polymers
                    and item.label in PolymerLabels
                    for item in self.tags
                ]),
                any([
                    not only_polymers
                    and item.label in PolymerLabels + ChemicalLabels
                    for item in self.tags
                ]),
            ])
        ]

        return all(criteria)

    def _group_consecutive_tags(self) -> list[types.NerLabelGroup]:
        """ Group all consecutive named entities that have the same label. """
        groups = []
        prev_group : types.NerLabelGroup = None

        for i in range(len(self.tags)):
            group = types.NerLabelGroup(
                start = i,
                end = i,
                text = self.tags[i].text,
                label = self.tags[i].label,
            )

            if prev_group and prev_group.label == group.label:
                # continuation of the same named entity
                prev_group.end = group.end
                if len(group.text) > 1:
                    text = " ".join([prev_group.text, group.text])
                else:
                    text = prev_group.text + group.text

                prev_group.text = RecordExtractor.cleanup_parentheses(text)
            elif prev_group is not None:
                # end of the last group
                groups.append(prev_group)
                prev_group = group
            else:
                prev_group = group

        # add the last group
        groups.append(prev_group)
        return groups
    
    @staticmethod
    def cleanup_parentheses(text : str) -> str:
        text = text.replace(' )', ')')
        text = text.replace(' }', '}')
        text = text.replace(' - ', '-')
        text = text.replace(' ( ', '(')
        text = text.replace('{ ', '{')
        text = text.replace(' _ ', '_')
        text = text.replace(' , ', ',')
        text = text.replace(' / ', '/')
        text = text.replace('( ', '(')
        text = text.replace("' ", "'")
        text = text.replace(" '", "'")
        text = text.replace('" ', '"')
        text = text.replace(' "', '"')
        text = text.replace('[ ', '[')
        text = text.replace(' ]', ']')
        text = text.replace(' : ', ':')
        if text.count('}') == text.count('{')-1:
            text = text+'}'
        if text.count(')') == text.count('(')-1:
            # Assumes the missing closing bracket is in the end which is reasonable
            text = text+')'
        elif text.count(')') == text.count('(')+1:
            # Last ) is being removed from the list of tokens which is ok
            text = text[:-1]
        return text


    def _find_chemdata_abbr(self, text):
        #@Todo: remove dependency on CDE
        para = Paragraph(text)
        return [
            (
                tuple_entity[0][0],
                RecordExtractor.cleanup_parentheses(' '.join(tuple_entity[1]))
            )
            for tuple_entity in para.abbreviation_definitions
        ]

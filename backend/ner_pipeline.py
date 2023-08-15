from backend import types

class RecordExtractor:
    def __init__(self, text : str, tags : list) -> None:
        self.text = text
        self.tags = tags

    def extract(self, only_polymers=False) -> list:
        if not self._check_relevance(only_polymers):
            return []
        groups = self._group_consecutive_tags()
        return groups

        
    def _check_relevance(self, only_polymers : bool) -> bool:
        """ Check if the text has name, property and values in it. """
        criteria = [
            'PROP_VALUE' in [item.label for item in self.tags],
            'PROP_NAME'  in [item.label for item in self.tags],
            any([
                any([
                    only_polymers
                    and item.label in ['POLYMER', 'MONOMER', 'POLYMER_FAMILY']
                    for item in self.tags
                ]),
                any([
                    not only_polymers
                    and item.label in ['POLYMER', 'MONOMER', 'POLYMER_FAMILY', 'ORGANIC', 'INORGANIC']
                    for item in self.tags
                ]),
            ])
        ]

        return all(criteria)

    def _group_consecutive_tags(self) -> list[types.NerLabelGroup]:
        """Group all consecutive tags that have the same entity label"""
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
                prev_group.text = " ".join([prev_group.text, group.text])
            elif prev_group is not None:
                # end of the last group
                groups.append(prev_group)
                prev_group = group
            else:
                prev_group = group

        # add the last group
        groups.append(prev_group)
        return groups

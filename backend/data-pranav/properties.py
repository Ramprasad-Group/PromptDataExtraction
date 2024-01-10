import json
import pandas as pd
import pylogg

from backend import sett

log = pylogg.New('dataset')

Corefs = {
    'Tg': [
        'Tg', 'T_{g}', 'T_{g}s', 'T_{g})',
        'glass transition temperature',
        'glass transition temperature T_{g}',
        'the glass transition temperature',
        'glass transition', 'glass transition temperatures',
    ],
    'bandgap': [
        'bandgap', 'band gap', 'band gaps', 'E_{g}',
        'optical band gap', 'optical bandgap',
    ],
    'HOMO': [
        'highest occupied molecular orbital energy',
        'highest occupied molecular orbital energy level',
        'highest occupied molecular orbital) energy level',
        'highest occupied molecular orbital energy levels',
        'Highest occupied molecular orbital energy levels',
        'highest occupied molecular orbital level',
        'hole',
        'hole mobilities',
        'hole mobility',
        'hole mobility μ',
        'HOMO',
        'HOMO and LUMO values',
        'HOMO energy',
        'HOMO) energy leve',
        'HOMO energy level',
        'HOMO) energy level',
        'HOMO energy levels',
        'HOMO) leve',
        'HOMO level',
        'HOMO levels',
    ],
    'LUMO': [
        'lowest unoccupied molecular orbital energy',
        'LUMO',
        'LUMO energy level',
        'LUMO energy levels',
        'LUMO/HOMO levels',
        'LUMO level',
        'LUMO) level',
        'LUMO levels',
    ],
    'Youngs modulus': [
        "Young's modulus"
    ],
    'Tensile strength' : [
        'tensile strength',
        'tensile strengths'
    ]
}


class LLMProperties:
    def __init__(self):
        """List of selected properties of LLM based extraction. """
        self.properties = pd.read_excel(sett.DataFiles.llm_properties_xl, sheet_name='PropertyList')
        log.info("Load OK: {}", sett.DataFiles.llm_properties_xl)

        self.metadata = {}
        with open(sett.DataFiles.properties_json) as fp:
            self.metadata = json.load(fp)
            log.info("Load OK: {}", sett.DataFiles.properties_json)


    def get_list(self) -> pd.DataFrame:
        mask = self.properties.FullTextSelect == 1
        selected = self.properties[mask]
        return selected

    def get_corefs(self, property) -> list[str]:
        property = property.lower()
        if property in self.metadata:
            return self.metadata[property]['property_list']
        else:
            log.warn("No metadata for property:", property)
            return []

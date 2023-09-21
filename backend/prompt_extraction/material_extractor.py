import pylogg
from rapidfuzz import process

from backend.utils import jsonl
from backend.prompt_extraction.crossref_extractor import CrossrefExtractor
from backend.record_extraction.base_classes import (
    MaterialMention, MATERIAL_CATEGORIES, COPOLYMER_INDICATORS, SOLVENTS,
)

log = pylogg.New('llm')


class MaterialExtractor:
    def __init__(self, crossref_extractor : CrossrefExtractor,
                 namelist_jsonl : str) -> None:

        self.crossref_extractor : CrossrefExtractor = crossref_extractor
        self.polymers = {
            line['polymer'] : line for line in jsonl.read_file(namelist_jsonl)
        }

    def parse_material(self, matstr : str) -> MaterialMention:
        material = MaterialMention()

        # Check against the list of known polymers.
        match = process.extractOne(
            matstr, list(self.polymers.keys()), score_cutoff=96)

        if match:
            name = match[0]
            material.material_class = "POLYMER"
            material.entity_name = name
            material.normalized_material_name = \
                self.polymers[name].get('normalized_name', '')
            material.polymer_type = self._detect_polymer_type(matstr.lower())
        # Check against the list of known solvents.
        elif matstr.lower() in SOLVENTS:
            material.entity_name = matstr
            material.material_class = 'SOLVENT'
        else:
            material.entity_name = matstr
            material.material_class = ""

        # Check against the list of known keywords.
        for category in MATERIAL_CATEGORIES:
            if category in matstr.lower():
                material.role = category
                break

        # Check if any abbreviation matches.
        for match in self.crossref_extractor.list_all(matstr):
            material.coreferents.append(match)

        return material
    
    
    def _detect_polymer_type(self, material_name : str) -> str:
        """Based on cues in the polymer name, detect the type of the polymer """
        copoly_criteria = [
            material_name.count('poly') > 1,
            any([
                subword in material_name for subword in COPOLYMER_INDICATORS
            ]),
            all([
                '-' in material_name,
                material_name.upper() == material_name
            ]),
        ]
        if 'star' in material_name:
            return 'star_polymer'
        elif any(copoly_criteria):
            return 'copolymer'
        else:
            return 'homopolymer'

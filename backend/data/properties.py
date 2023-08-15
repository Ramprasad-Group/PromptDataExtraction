import json
import pandas as pd
import pylogg
import sett

log = pylogg.New('dataset')

class LLMProperties:
    def __init__(self):
        """List of selected properties of LLM based extraction. """
        self.properties = pd.read_excel(sett.Dataset.llm_properties_xl, sheet_name='PropertyList')
        log.info("Load OK: {}", sett.Dataset.llm_properties_xl)

        self.metadata = {}
        with open(sett.Dataset.properties_json) as fp:
            self.metadata = json.load(fp)
            log.info("Load OK: {}", sett.Dataset.properties_json)


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

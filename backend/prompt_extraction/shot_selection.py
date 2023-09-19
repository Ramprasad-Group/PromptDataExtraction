import json
import pylogg
import random

from backend.postgres.orm import CuratedData, PaperTexts

log = pylogg.New("shot")

class ShotSelector:
    def __init__(self, min_records) -> None:
        self.curated = {}
        self.min_records = min_records

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return name
    
    def save_curated_dataset(self, filename : str):
        with open(filename, 'w') as fp:
            json.dump(self.curated, fp)
        log.done("Save curated dataset: {}", filename)

    def load_curated_dataset(self, filename : str):
        with open(filename) as fp:
            dataset = json.load(fp)
        
        self.curated = self._filter_min_records(dataset)
        log.done("Load curated dataset: {}", filename)


    def build_curated_dataset(self, db, criteria : dict = {}):
        # Retrive the curated data from database.
        dataset = {}
        t2 = log.info("Building curated dataset.")
        curated : list[CuratedData] = CuratedData().get_all(db, criteria)
        n = 0
        for data in curated:
            if data.para_id not in dataset:
                # get the text
                paragraph : PaperTexts = PaperTexts().get_one(
                    db, criteria = { 'id': data.para_id }
                )
                if not paragraph:
                    log.error(
                        "Failed to retrived paragraph {} for curated data: {}",
                        data.para_id, data.id)
                    continue
                dataset[data.para_id] = {
                    'text': paragraph.text,
                    'doi': paragraph.doi,
                    'records': []
                }
            record = {
                'material': data.material,
                'property': data.property_name,
                'value': data.property_value
            }
            dataset[data.para_id]['records'].append(record)
            n += 1

        self.curated = self._filter_min_records(dataset)
        t2.note("Added {} records to curated dataset.", n)


    def _filter_min_records(self, dataset : dict):
        log.info("Filtering curated data with min {} records.",
                 self.min_records)
        return {
            k : v for k,v in dataset.items()
            if len(v['records']) > self.min_records
        }
    
    def get_best_shots(self, text : str, n : int = 1):
        raise NotImplementedError()
    

class RandomShotSelector(ShotSelector):
    def __init__(self, min_records : int = 2) -> None:
        super().__init__(min_records)
    
    def get_best_shots(self, text: str, n: int = 1):
        choices = random.sample(list(self.curated.keys()), n)
        return [ self.curated[c] for c in choices ]
    

class DiverseShotSelector(ShotSelector):
    def __init__(self, ner_model : str, device : int, prop_meta_json : str,
                 min_records : int = 2) -> None:
        from backend.record_extraction import bert_model, utils
        from backend.prompt_extraction import embeddings

        super().__init__(min_records)
        prop_metadata = utils.load_property_metadata(prop_meta_json)

        bert = bert_model.MaterialsBERT(ner_model)
        bert.init_local_model(device)
        self.embed = embeddings.Embeddings(bert, prop_metadata)

    
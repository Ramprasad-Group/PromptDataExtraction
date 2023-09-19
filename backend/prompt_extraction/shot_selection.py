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
        return {
            k : v for k,v in dataset.items()
            if len(v['records']) > self.min_records
        }
        
    def get_best_shot(self, text):
        raise NotImplementedError()
    

class RandomShotSelector(ShotSelector):
    def __init__(self, min_records : int = 2) -> None:
        super().__init__(min_records)
    
    def get_best_shot(self, text : str = None) -> dict:
        """ Return a random choice from the curated data. """
        choice = random.choice(list(self.curated.keys()))
        return self.curated[choice]
    

import json
import pylogg
import random

import numpy as np
from sklearn.cluster import KMeans
from backend.postgres.orm import CuratedData, PaperTexts, PropertyMetadata

log = pylogg.New("shot")


class ShotSelector:
    def __init__(self, min_records) -> None:
        self.curated = {}
        self.embeddings = {}
        self.min_records = min_records

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return name

    def save_curated_dataset(self, filename: str):
        with open(filename, 'w') as fp:
            json.dump(self.curated, fp, indent=4)
        log.done("Save curated dataset: {}, {} items",
                 filename, len(self.curated))

    def load_curated_dataset(self, filename: str):
        with open(filename) as fp:
            dataset = json.load(fp)

        self.curated = self._filter_min_records(dataset)
        log.done("Load curated dataset: {}", filename)

    def save_embeddings(self, filename: str):
        with open(filename, 'w') as fp:
            json.dump({
                k : v.tolist() for k, v in self.embeddings.items()
            }, fp)
        log.done("Save embeddings: {}, {} items",
                 filename, len(self.embeddings))

    def load_embeddings(self, filename: str):
        with open(filename) as fp:
            dataset = { k : np.array(v) for k, v in json.load(fp).items() }
        self.embeddings = dataset
        assert len(self.embeddings) == len(self.curated), \
            "Embedings and dataset doesnot match, please recompute."
        log.done("Load embeddings: {}", filename)

    def build_curated_dataset(self, db, save_file: str, criteria: dict = {}):
        """ Build the curated dataset for shot selection.
            dataset = {
                para_id : {
                    'text': ...,
                    'doi': ...,
                    'records': [{}, ...],
                    'keywords': [],
                }
            }
        """
        t2 = log.info("Building curated dataset.")
        try:
            self.load_curated_dataset(save_file)
        except:
            # Retrive the curated data from database.
            curated: list[CuratedData] = CuratedData().get_all(db, criteria)
            for data in curated:
                if data.para_id not in self.curated:
                    # get the text
                    paragraph: PaperTexts = PaperTexts().get_one(
                        db, criteria={'id': data.para_id}
                    )
                    if not paragraph:
                        log.error(
                            "Failed to retrived paragraph {} for curated data: {}",
                            data.para_id, data.id)
                        continue
                    self.curated[data.para_id] = {
                        'text': paragraph.text,
                        'doi': paragraph.doi,
                        'records': [],
                        'keywords': set(),
                    }
                record = {
                    'material': data.material,
                    'property': data.property_name,
                    'value': data.property_value,
                    'conditions': data.conditions if data.conditions else "None",
                }
                self.curated[data.para_id]['keywords'].add(data.property_name)
                self.curated[data.para_id]['keywords'].add(data.material)
                for item in data.material_coreferents:
                    self.curated[data.para_id]['keywords'].add(item)
                for item in self._get_property_coreferents(db, data.property_name):
                    self.curated[data.para_id]['keywords'].add(item)

                self.curated[data.para_id]['records'].append(record)

            db.close()

            # Convert set to list for saving with json
            for para_id in self.curated:
                self.curated[para_id]['keywords'] = list(
                    self.curated[para_id]['keywords'])

            self.save_curated_dataset(save_file)

        # Downselect based on minimum record count
        self.curated = self._filter_min_records(self.curated)
        t2.note("Added {} records to curated dataset.", len(self.curated))

    def _get_property_coreferents(self, db, property_name) -> list[str]:
        meta: PropertyMetadata = PropertyMetadata().get_one(db, {
            'name': property_name
        })
        if meta:
            return meta.other_names
        else:
            return []

    def _filter_min_records(self, dataset: dict):
        log.info("Filtering curated data with min {} records.",
                 self.min_records)
        return {
            k: v for k, v in dataset.items()
            if len(v['records']) > self.min_records
        }

    def compute_embeddings(
            self, ner_model: str, device: int = 0, save_file : str = None):
        pass

    def get_best_shots(self, text: str, n: int = 1):
        raise NotImplementedError()


class RandomShotSelector(ShotSelector):
    def __init__(self, min_records: int = 2) -> None:
        super().__init__(min_records)

    def get_best_shots(self, text: str, n: int = 1):
        """ Randomly return n items from the curated dataset. """
        choices = random.sample(list(self.curated.keys()), n)
        return [self.curated[c] for c in choices]


class DiverseShotSelector(ShotSelector):
    def __init__(self, min_records: int = 2) -> None:
        import spacy
        from backend.record_extraction import bert_model

        super().__init__(min_records)

        self.nlplang = spacy.load('en_core_web_sm')
        self.bert = bert_model.MaterialsBERT()

    def get_best_shots(self, text: str, n: int = 1):
        """ Get the most diverse n items based on text embeddings
        of the curated data. """

        if not self.embeddings:
            raise RuntimeError("Embeddings not computed")

        Xt = np.array([embed for embed in self.embeddings.values()])
        kmeans = KMeans(n_clusters=n)
        kmeans.fit(Xt)

        cluster_centers = kmeans.transform(Xt).argmin(axis=0)
        diverse_paras = [
            list(self.embeddings.keys())[i] for i in cluster_centers
        ]

        return [self.curated[para_id] for para_id in diverse_paras]

    def compute_embeddings(self, ner_model: str, device: int = 0,
                           save_file : str = None):
        """ Compute embeddings of the curated texts using the BERT model. """
        if not self.curated:
            raise RuntimeError("Curated dataset not loaded.")
        
        try:
            self.load_embeddings(save_file)
        except:
            self.bert.init_local_model(ner_model, device)

            t2 = log.info("Computing text embeddings for {} text items.",
                        len(self.curated))

            for para_id, data in self.curated.items():
                text = self._get_relevant_sentences(data['text'], data['keywords'])
                self.embeddings[para_id] = self.bert.get_text_embeddings(text)

            t2.done("Embeddings computed.")
            if save_file is not None:
                self.save_embeddings(save_file)

    def _get_relevant_sentences(self, text, keywords) -> str:
        """ Select only the sentences that contain one of the keywords. """
        relevant_sentences = []
        doc = self.nlplang(text)
        for sentence in doc.sents:
            if any([word in sentence.text for word in keywords]):
                relevant_sentences.append(sentence.text)
        return " ".join(relevant_sentences)

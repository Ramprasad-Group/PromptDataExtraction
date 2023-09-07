"""
Test the NER pipeline.
USAGE: pytest tests/test_pipeline.py -s

"""

import os
import json
import pytest
import sett
from backend import ner_pipeline
from backend.nlp import ner
from backend.text import normalize
from backend.types import NerTag, NerLabelGroup

pytestmark = pytest.mark.filterwarnings("ignore")

@pytest.fixture
def bert():
    """ Load the MaterialsBERT model and return the model handle. """
    bertModel = ner.MaterialsBERT(sett.NerModel.model)
    bertModel.init_local_model(device=0)
    return bertModel

@pytest.fixture
def dataset():
    """ Return a list of (doi, text) tuples from Tg ground dataset. """
    datajson = os.path.join(os.path.dirname(__file__), "tg_ground_data.json")
    with open(datajson) as fp:
        data = json.load(fp)
    abstracts = []
    for k, v in data.items():
        for item in v:
            if item['abstract']:
                abstracts.append((k, item['abstract']))
    return abstracts

# def test_bert(bert):
#     text =  "Single‐layer pristine CVD‐graphene on 300 nm SiO_{2}/Si substrate was purchased from Hefei Vigon Material Technology Co., Ltd. (China)."
#     tags = bert.get_tags(text)
#     groups = ner.group_consecutive_tags(tags)
#     print(tags)
#     print(groups)
#     assert len(tags) > 0
#     assert type(tags[0]) == NerTag
#     assert type(groups[0]) == NerLabelGroup

# def test_extractor(bert):
#     text =  "Single‐layer pristine CVD‐graphene on 300 nm SiO_{2}/Si substrate was purchased from Hefei Vigon Material Technology Co., Ltd. (China)."
#     tags = bert.get_tags(text)
#     groups = ner.group_consecutive_tags(tags)

#     extractor = ner_pipeline.TextDataExtractor(text, tags)
#     extractor._identify_entities(groups)
#     print(extractor.materials)

# def print_sentence(*args):
#     print("Arguments:", *args)

# def test_process_sentence(bert):
#     text = """
#     Electrochemical fluorination of triphenylmethane in the U‐shaped cell equipped
#     with an s‐BPE was carried out in a MeCN solution containing 5 mM of CsF, 0.6 M
#     of PEG (600) and 5 mM of triphenylmethane. 100 V of cell voltage was applied
#     between Pt driving electrodes with the s‐BPE composed of ITO or Pt, the current
#     through the s‐BPE was monitored with an ammeter at 25 °C for 4 F/mol. After
#     the electrolysis, the reaction mixture was extracted with hexane, and the
#     hexane solution was evaporated under reduced pressure. Product yields were
#     obtained by ^{19}F NMR using monofluorobenzene as an internal standard.
#     """
#     text = normalize.normText(text)
#     tags = bert.get_tags(text)
#     groups = ner.group_consecutive_tags(tags)
#     ner.process_sentence(groups, print_sentence, 2)


def test_pipeline(bert, dataset):
    for doi, text in dataset:
        text = normalize.normText(text)
        tags = bert.get_tags(text)
        extractor = ner_pipeline.TextDataExtractor(text, tags)
        mat = extractor.extract(debug=True)
        mat._detect_polymer_type()
        print(doi, mat.abbreviation_pairs)

    # breakpoint()

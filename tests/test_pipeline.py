import pytest
import sett
from backend import ner_pipeline
from backend.nlp import ner
from backend.types import NerTag, NerLabelGroup

pytestmark = pytest.mark.filterwarnings("ignore")

@pytest.fixture
def bert():
    bertModel = ner.MaterialsBERT(sett.NerModel.model)
    bertModel.init_local_model(device=0)
    return bertModel

def test_bert(bert):
    text =  "Single‐layer pristine CVD‐graphene on 300 nm SiO_{2}/Si substrate was purchased from Hefei Vigon Material Technology Co., Ltd. (China)."
    tags = bert.get_tags(text)
    groups = ner.group_consecutive_tags(tags)
    print(tags)
    print(groups)
    assert len(tags) > 0
    assert type(tags[0]) == NerTag
    assert type(groups[0]) == NerLabelGroup

def test_extractor(bert):
    text =  "Single‐layer pristine CVD‐graphene on 300 nm SiO_{2}/Si substrate was purchased from Hefei Vigon Material Technology Co., Ltd. (China)."
    tags = bert.get_tags(text)
    groups = ner.group_consecutive_tags(tags)

    extractor = ner_pipeline.TextDataExtractor(text, tags)
    extractor._identify_entities(groups)
    print(extractor.materials)

# Logic for extracting material amounts
from base_classes import MaterialAmount, EntityList, RecordProcessor


class MaterialAmountExtractor(RecordProcessor):
    def __init__(self, grouped_spans, logger=None):
        super(MaterialAmountExtractor, self).__init__()
        self.grouped_spans = grouped_spans
        self.logger = logger
        self.material_amounts = EntityList()

    def material_amount_infer(self, sentence, labels):
        for i, span in enumerate(sentence):
            if span.label == 'MATERIAL_AMOUNT':
                j=1
                while i+j<len(sentence) or i-j>=0:
                    if i+j<len(sentence) and sentence[i+j].label in self.material_entities:
                        self.material_amounts.entity_list.append(MaterialAmount(entity_name=sentence[i+j].text, material_amount=span.text))
                        break
                    elif i-j>=0 and sentence[i-j].label in self.material_entities:
                        self.material_amounts.entity_list.append(MaterialAmount(entity_name=sentence[i-j].text, material_amount=span.text))
                        break
                    j+=1
    def run(self):
        self.process_sentence(self.grouped_spans, self.material_amount_infer)
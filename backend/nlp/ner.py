import spacy
import pylogg

from backend.types import NerTag
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

logger = pylogg.New('ner')


class MaterialsBERT:
    def __init__(self, model) -> None:
        self.nlp = spacy.load("en_core_web_sm")
        self.model = model
        self.pipeline = None

    def init_local_model(self, device):
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.model, model_max_length=512)
        model = AutoModelForTokenClassification.from_pretrained(self.model)
        self.pipeline = pipeline(task="ner", model=model, tokenizer=tokenizer,
                                aggregation_strategy="simple",
                                device=device)
        logger.info("Loaded materials bert.")

    def get_tags(self, text : str):
        """ Return NER labels for a text. """
        tokens = self.pipeline(text)
        return self._ner_feed(tokens, text)

    def _ner_feed(self, seq_pred, text) -> list[NerTag]:
        """ Convert outputs of the NER to a form usable by record extraction
            seq_pred: List of dictionaries
            text: str, text fed to sequence classification model
        """
        doc = self.nlp(text)
        token_label = NerTag
        if len(seq_pred) == 0:
            # If no NER could be reconginzed, the prediction list would be empty.
            return [token_label(doc[i].text, 'O') for i in range(len(doc))]

        seq_index = 0
        text_len = len(text)
        seq_len = len(seq_pred)
        len_doc = len(doc)
        token = ''
        token_labels = []
        start_index = seq_pred[seq_index]["start"]
        end_index = seq_pred[seq_index]["end"]
        i = 0
        char_index = -1

        while i < len_doc:
            token = doc[i].text
            if char_index+1 >= start_index and seq_index < seq_len:
                # Continue loop till end_index or end of word
                # increment index and values
                current_label = seq_pred[seq_index]["entity_group"]
                while char_index < end_index-1:
                    token_labels.append(token_label(token, current_label))
                    char_index += len(token)
                    if char_index < text_len-1 and text[char_index+1] == ' ': char_index+=1
                    i += 1
                    if i < len_doc: token=doc[i].text
                seq_index += 1
                if seq_index < seq_len:
                    start_index = seq_pred[seq_index]["start"]
                    end_index = seq_pred[seq_index]["end"]
            else:
                token_labels.append(token_label(token, 'O'))
                i += 1
                char_index += len(token)
                if char_index < text_len-1 and text[char_index+1] == ' ':
                    char_index += 1
        
        return token_labels


from backend.types import NerTag, NerLabelGroup
from chemdataextractor.doc import Paragraph

PolymerLabels = ['POLYMER', 'MONOMER', 'POLYMER_FAMILY']
ChemicalLabels = ['ORGANIC', 'INORGANIC']


def check_relevant_ners(tags : list[NerTag],
                        only_polymers : bool) -> bool:
    """ Return True if all of name, property and values are available
        in the predicted NER tags.
        
        tags :
            List of NerTags extracted using MaterialsBERT.

        only_polymers : 
            Return true only if polymer tags are found, else return true
            if organic or inorganic tags are also found.
    """
    criteria = [
        'PROP_VALUE' in [item.label for item in tags],
        'PROP_NAME'  in [item.label for item in tags],
        any([
            any([
                only_polymers
                and item.label in PolymerLabels
                for item in tags
            ]),
            any([
                not only_polymers
                and item.label in PolymerLabels + ChemicalLabels
                for item in tags
            ]),
        ])
    ]

    return all(criteria)


def group_consecutive_tags(tags : list[NerTag]) -> list[NerLabelGroup]:
    """ Group all consecutive NER tags that have the same label.
        
        tags :
            List of NER tags extracted using a BERT model.

        Returns the list of NER tags with consecutive tags combined together.
    """
    groups = []
    prev_group : NerLabelGroup = None

    for i in range(len(tags)):
        group = NerLabelGroup(
            start = i,
            end = i,
            text = tags[i].text,
            label = tags[i].label,
        )

        if prev_group and prev_group.label == group.label:
            # continuation of the same named entity
            prev_group.end = group.end
            if len(group.text) > 1:
                text = " ".join([prev_group.text, group.text])
            else:
                text = prev_group.text + group.text

            prev_group.text = cleanup_parentheses(text)
        elif prev_group is not None:
            # end of the last group
            groups.append(prev_group)
            prev_group = group
        else:
            prev_group = group

    # add the last group
    groups.append(prev_group)
    return groups


def cleanup_parentheses(text : str) -> str:
    """ Normalize and clean up parentheses and brackets by removing
        spaces and extras.

        text :
            The text to clean up.
    """
    text = text.replace(' )', ')')
    text = text.replace(' }', '}')
    text = text.replace(' - ', '-')
    text = text.replace(' ( ', '(')
    text = text.replace('{ ', '{')
    text = text.replace(' _ ', '_')
    text = text.replace(' , ', ',')
    text = text.replace(' / ', '/')
    text = text.replace('( ', '(')
    text = text.replace("' ", "'")
    text = text.replace(" '", "'")
    text = text.replace('" ', '"')
    text = text.replace(' "', '"')
    text = text.replace('[ ', '[')
    text = text.replace(' ]', ']')
    text = text.replace(' : ', ':')
    if text.count('}') == text.count('{')-1:
        text = text+'}'
    if text.count(')') == text.count('(')-1:
        # Assumes the missing closing bracket is in the end which is reasonable
        text = text+')'
    elif text.count(')') == text.count('(')+1:
        # Last ) is being removed from the list of tokens which is ok
        text = text[:-1]
    return text


def find_chemdata_abbr(text : str) -> list[tuple]:
    """ Find a list of abbreviations defined in a text using ChemDataExtractor.
        Returns a list of tuples containing abbreviations and full forms.

        text :
            The text to search for abbreviations.

    """
    para = Paragraph(text)
    return [
        (abbr[0][0], cleanup_parentheses(' '.join(abbr[1])))
        for abbr in para.abbreviation_definitions
    ]

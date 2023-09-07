import spacy
import pylogg
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from backend.text import normalize
from backend.types import NerTag, NerLabelGroup
from chemdataextractor.doc import Paragraph

ChemicalLabels = ['ORGANIC', 'INORGANIC']
PolymerLabels = ['POLYMER', 'MONOMER', 'POLYMER_FAMILY']
PropertyLabels = ['PROP_NAME', 'PROP_VALUE', 'MATERIAL_AMOUNT']

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

            prev_group.text = normalize.normText(text)

        elif prev_group is not None:
            # end of the last group
            groups.append(prev_group)
            prev_group = group
        else:
            prev_group = group

    # add the last group
    groups.append(prev_group)
    return groups


def find_chemdata_abbr(text : str) -> list[tuple]:
    """ Find a list of abbreviations defined in a text using ChemDataExtractor.
        Returns a list of tuples containing abbreviations and full forms.

        text :
            The text to search for abbreviations.
    """
    para = Paragraph(text)
    return [
        (abbr[0][0], normalize.cleanup_parentheses(' '.join(abbr[1])))
        for abbr in para.abbreviation_definitions
    ]


def process_sentence(grouped_spans : list[NerLabelGroup],
                     callback : callable, sentence_limit : int = None):
    """
    Extract indidividual sentences and their labels from a list
    of NerLabelGroup.
    Each individual sentences and labels are passed to the callback.
    An optional limit can be specified to process only that many
    sentences. Sentences are identified using the dot (.) character.
    """

    # if no consecutive group is defined in the list, return
    if not grouped_spans:
        return
    
    len_span = len(grouped_spans)
    i = 0
    sentence_num = 0

    # for each consecutive groups in the list
    while i < len_span:
        # get the text
        current_token = grouped_spans[i].text
        current_sentence = []
        labels = [] # Labels stored separately in order to do a quick scan of the sentence while processing it

        # a token can be .
        while (current_token != '.') and i < len_span:
            # Assuming that . at the end of a token can only be a tokenization error
            # The above solution is one simple way of fixing this, the other way is to test a deeper tokenization model
            # We could also impose the additional constraint that the second condition only happen for recognized entity types 
            # since that is where there is likely to be parsing failure

            # get the text
            current_token = grouped_spans[i].text

            # add the text as current sentence
            current_sentence.append(grouped_spans[i])

            # add the corresponding label
            labels.append(grouped_spans[i].label) # Might remove

            # next group
            i += 1

            if not current_token:
                print(f'Blank current_token found = {current_token}')

            # if the last character is a period, break
            # Assumes that a . at the end of a token must belong to a period.
            # It could also belong to an abbreviation that we cannot disambiguate through this.
            if current_token[-1]=='.':
                break
            # if i < len_span: current_token = grouped_spans[i].text

        # Process the sentence to extract propery value pairs
        callback(current_sentence, labels)

        # This condition takes care of cases when consecutive periods occur in a sentence
        if current_token == '.' and i < len_span and grouped_spans[i].text == '.':
            i += 1

        if sentence_limit and sentence_num > sentence_limit:
            break

        sentence_num += 1

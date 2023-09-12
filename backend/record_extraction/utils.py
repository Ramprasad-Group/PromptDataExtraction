import json
import spacy
from collections import namedtuple

def token_post_processing(input_token):
    input_token = input_token.replace(' )', ')').replace(' }', '}').replace(' - ', '-').replace(' ( ', '(').replace('{ ', '{').replace(' _ ', '_').replace(' , ', ',').replace(' / ', '/').replace('( ', '(').replace("' ", "'").replace(" '", "'").replace('" ', '"').replace(' "', '"').replace('[ ', '[').replace(' ]', ']').replace(' : ', ':')
    if len(input_token)>=2 and input_token.count(')') == input_token.count('(')-1:
        input_token = input_token+')' # Assumes the missing closing bracket is in the end which is reasonable
    elif len(input_token)>=2 and input_token.count('}') == input_token.count('{')-1:
        input_token = input_token+'}'
    elif len(input_token)>=2 and input_token.count(')') == input_token.count('(')+1: # Last ) is being removed from the list of tokens which is ok
        input_token = input_token[:-1]

    return input_token

def date_conversion(doc):
    year, month, day = doc['year'], doc['month'], doc['day']
    month_dict = {1: 31, 2:28, 3: 31, 4:30, 5:31, 6: 30, 7:31, 8:31, 9: 30, 10:31, 11:30, 12: 31}
    day_count = sum([month_dict[key] for key in range(1, month)])
    assert day_count<=365
    year_fraction = (day_count+day)/365
    return year+year_fraction

def property_token_postprocessing(prop_name):
    """Correct for any sequence labeling noise through a post-processing step"""
    if prop_name[-1]==')' and prop_name.count(')')>prop_name.count('('):
        prop_name = prop_name[:-1]
    elif prop_name[-1]=='}' and prop_name.count('}')>prop_name.count('{'):
        prop_name = prop_name[:-1]

def process_sentence(grouped_spans, callback, sentence_limit=None):
    # Associate property values with the closest property name in the same sentence
    # Operate on grouped_entities
    # Use dot to determine sentence boundary
    # Need to include material amount existence and material_name existence in loop
    # Creates a single sentence out of grouped spans
    if grouped_spans:
        len_span = len(grouped_spans)
        i = 0
        sentence_num = 0
        while i < len_span:
            current_token = grouped_spans[i].text
            current_sentence = []
            labels = [] # Labels stored separately in order to do a quick scan of the sentence while processing it
            while current_token != '.' and i < len_span:
                current_token = grouped_spans[i].text
                current_sentence.append(grouped_spans[i])
                labels.append(grouped_spans[i].label) # Might remove
                i+=1
            callback(current_sentence, labels)
            # This condition takes care of cases when consecutive periods occur in a sentence
            if current_token == '.' and i < len_span and grouped_spans[i].text == '.':
                i+=1
            if sentence_limit and sentence_num>sentence_limit:
                break
            sentence_num+=1
            # Process the sentence to extract propery value pairs

def ner_feed(seq_pred, text):
        """Convert outputs of the NER to a form usable by record extraction
            seq_pred: List of dictionaries
            text: str, text fed to sequence classification model
        """
        seq_index = 0
        text_len = len(text)
        seq_len = len(seq_pred)
        start_index = seq_pred[seq_index]["start"]
        end_index = seq_pred[seq_index]["end"]
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        len_doc = len(doc)
        token = ''
        token_labels = []
        token_label = namedtuple('token_label', ["text", "label"])
        i = 0
        char_index = -1
        while i < len_doc:
            token = doc[i].text
            if char_index+1>=start_index and seq_index<seq_len:
                # Continue loop till end_index or end of word
                # increment index and values
                current_label = seq_pred[seq_index]["entity_group"]
                while char_index < end_index-1:
                    token_labels.append(token_label(token, current_label))
                    char_index+=len(token)
                    if char_index<text_len-1 and text[char_index+1]==' ': char_index+=1
                    i+=1
                    if i < len_doc: token=doc[i].text
                seq_index+=1
                if seq_index < seq_len:
                    start_index = seq_pred[seq_index]["start"]
                    end_index = seq_pred[seq_index]["end"]
            else:
                token_labels.append(token_label(token, 'O'))
                i+=1
                char_index += len(token)
                if char_index<text_len-1 and text[char_index+1]==' ': char_index+=1
        
        return token_labels 

class LoadNormalizationDataset:
    def __init__(self, curated_normalized_data=None):
        if curated_normalized_data is None:
            self.curated_normalized_data = ''
        else:
            self.curated_normalized_data = curated_normalized_data

    def process_normalization_files(self):
        """Read the json files associated with normalization and return them"""
        with open(self.curated_normalized_data, 'r') as fi:
            train_data_text = fi.read()
        train_data = json.loads(train_data_text)

        return train_data

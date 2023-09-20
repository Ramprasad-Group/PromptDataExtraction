from collections import namedtuple

import spacy
import torch
import pylogg
from transformers import (
    AutoModelForTokenClassification, AutoTokenizer, pipeline
)

logger = pylogg.New('bert')

class MaterialsBERT:
    def __init__(self, model) -> None:
        self.nlp = spacy.load("en_core_web_sm")
        self.model = model
        self.tokenizer = None
        self.pipeline = None

    def init_local_model(self, device=0):
        # Load model and tokenizer
        t1 = logger.trace("Loading bert model to device = {}.", device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model,
                                                  model_max_length=512)
        model = AutoModelForTokenClassification.from_pretrained(self.model)
        self.pipeline = pipeline(
            task="ner", model=model, tokenizer=self.tokenizer,
            aggregation_strategy="simple", device=device)
        t1.done("Loaded bert model.")

    def get_tags(self, text: str):
        """ Return NER labels for a text. """
        tokens = self.pipeline(text)
        return self._ner_feed(tokens, text)
        # return ner_feed(tokens, text)

    def get_text_embeddings(self, text : str):
        """ Compute the embeddings for the given text.
            Returns a numpy array containing the text embeddings.
        """

        # Tokenize the sentences
        encoded_inputs = self.tokenizer(text, padding=True, truncation=True,
                                        max_length=512, return_tensors='pt')

        # Obtain the embeddings from the model.
        # There may be more ways to do this,
        # can use the CLS token embedding as well.
        with torch.no_grad():
            outputs = self.model(**encoded_inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze(0)

        return embeddings.numpy()


    def _ner_feed(self, seq_pred, text) -> list:
        """ Convert outputs of the NER to a form usable by record extraction
            seq_pred: List of dictionaries
            text: str, text fed to sequence classification model
        """
        doc = self.nlp(text)
        token_label = namedtuple('token_label', ["text", "label"])
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
                    if char_index < text_len-1 and text[char_index+1] == ' ':
                        char_index += 1
                    i += 1
                    if i < len_doc:
                        token = doc[i].text
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

""" Process NER request using Materials BERT.

    There are two options to run the Materals BERT model.
        1. Run inside the UI process.
        2. Run with PolyAI and use API request to get the NER tags.

"""
import os
import streamlit as st

import polyai.api
from polyai.api.helpers import model_ner

from frontend.base import Container

# Global UI state
G = st.session_state

class NERTagger(Container):
    """ A webpage div that handles NER related interactions. """
    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("POLYAI_API_KEY", None)
        if not api_key:
            raise ValueError("POLYAI_API_KEY not set.")
        polyai.api.api_key = api_key

    def get_ner_tags(self, text):
        """ Send API request to polyai to get the NER labels of a text. """
        print("Sending NER api request ...")
        resp = polyai.api.BERTNER.create( model="materialsbert", text=text)
        ner_map = model_ner(resp)
        return ner_map

""" Process NER request using Materials BERT.

    There could be two options to run the Materals BERT model.
        1. Run inside the UI process.
        2. Run with PolyAI and use API request to get the NER tags.

"""
import streamlit as st
from frontend.base import Container

# Global UI state
G = st.session_state

class NERTagger(Container):
    """ A webpage div that handles NER related interactions. """
    def __init__(self) -> None:
        super().__init__()

    def show(self):
        return super().show()

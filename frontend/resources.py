import streamlit as st
import pylogg
import sett

logger = pylogg.New('res')
sett.load_settings()

@st.cache_resource
def postgres():
    """ Connect to the postgres database. """
    from backend import postgres
    postgres.load_settings()
    db = postgres.connect()
    logger.info("PostGres connected.")
    return db

@st.cache_resource
def materials_bert():
    """ Return the materials bert pipeline handler. """
    from backend.nlp import ner
    bert = ner.MaterialsBERT(sett.NerModel.model)
    bert.init_local_model(sett.NerModel.pytorch_device)
    return bert

@st.cache_resource
def selected_properties():
    """ Class to handle selected list of properties. """
    from backend.data.properties import LLMProperties
    return LLMProperties()

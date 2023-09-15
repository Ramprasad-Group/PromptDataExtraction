import pylogg
import streamlit as st
from backend import sett

logger = pylogg.New('res')
sett.load_settings()

@st.cache_resource
def postgres():
    """ Connect to the postgres database. """
    from backend import postgres
    postgres.load_settings()
    db = postgres.connect()
    return db

@st.cache_resource
def materials_bert():
    """ Return the materials bert pipeline handler. """
    from backend.record_extraction import bert_model
    bert = bert_model.MaterialsBERT(sett.NERPipeline.model)
    bert.init_local_model(device=sett.NERPipeline.pytorch_device)
    return bert

@st.cache_resource
def selected_properties():
    """ Class to handle selected list of properties. """
    from backend.data.properties import LLMProperties
    return LLMProperties()

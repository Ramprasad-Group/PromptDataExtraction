""" Draw and update the sidebar. """

import streamlit as st
from frontend.base import Container

# Global state
G = st.session_state

class Sidebar:
    def __init__(self) -> None:
        if 'prop_list' not in G:
            G.prop_list = []

        with st.sidebar:
            st.write("Sidebar initialized ...")

    def show():
        pass

""" Draw and update the sidebar. """

import streamlit as st
from frontend.base import Container

class Sidebar:
    def __init__(self) -> None:
        with st.sidebar:
            st.write("Sidebar initialized ...")

    def show():
        pass

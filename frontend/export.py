""" Handle file exports to download by user.

Use pandas to easily convert to CSV, JSONL or other formats.
For download purposes, we will use the simple static file handler by streamlit.

"""
import pandas as pd
import streamlit as st
from frontend.base import Container, StaticFile

# Global UI state
G = st.session_state

class Exporter(Container):
    def __init__(self) -> None:
        super().__init__()


    def show(self, df : pd.DataFrame, name : str):
        """ Show links to download a Pandas dataframe. """
        csv_url = self.as_csv(df, name)
        json_url = self.as_json(df, name)
        jsonl_url = self.as_jsonlines(df, name)
        with self.div:
            st.markdown(f"Download: [CSV]({csv_url}) [JSON]({json_url}) ")
            st.markdown(f"[JSONL]({jsonl_url})")


    def as_csv(self, df : pd.DataFrame, filename : str) -> str:
        """ Given a dataframe, convert to CSV.
        Return a url to download the file.
        """
        file = StaticFile(filename)
        df.to_csv(file.path)
        print("Save OK:", file.path)
        return file.url


    def as_jsonlines(self, df : pd.DataFrame, filename : str) -> str:
        """ Given a dataframe, convert to JSON lines.
        Return a url to download the file.
        """
        file = StaticFile(filename)
        df.to_json(file.path, orient="records", lines=True)
        print("Save OK:", file.path)
        return file.url


    def as_json(self, df : pd.DataFrame, filename : str) -> str:
        """ Given a dataframe, convert to JSON.
        Return a url to download the file.
        """
        file = StaticFile(filename)
        df.to_json(file.path, lines=False)
        print("Save OK:", file.path)
        return file.url

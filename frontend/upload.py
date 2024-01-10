""" Handle file uploads by user.

Currently only support XML or HTML.
Future: PDF, Zip files.

"""
import streamlit as st
from frontend.base import Container

# Global UI state
G = st.session_state

class Uploader(Container):
    """ A webpage div that handles NER related interactions. """
    def __init__(self) -> None:
        super().__init__()
        self.file = None

    def show(self):
        # show the file uploader
        uploader_label = "Choose a paper to extract data:"
        with self.div:
            self.file = st.file_uploader(uploader_label, type=["xml", "html"],
                                         accept_multiple_files=False)
            G.uploadOK = False

    def get_file_content(self) -> str | None:
        """ Return the content string of an uploaded file. """
        if self.file:
            content = self.file.read()
            G.uploadOK = True
        else:
            content = None

        return content

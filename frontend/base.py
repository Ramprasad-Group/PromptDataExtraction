""" Streamlit base classes. """
import os
import urllib.parse
import streamlit as st


class Container:
    """ Initialize a container/div area in the webpage. """
    def __init__(self) -> None:
        self.div : st._DeltaGenerator = st.container()
        self.div.empty()

        # if sett.Run.debug:
        #     with self.div:
        #         st.write(f"[{self.__class__.__name__} area]")

    def show(self):
        raise NotImplementedError(f"{self.__class__.__name__}.show()")


class StaticFile:
    """ Create a new static file to serve via http.
        Note!! Streamlit will not handle binary files other than images.
    """
    def __init__(self, name : str) -> None:
        self.static = "static"
        self.name = name

    @property
    def path(self):
        """ Server path to save the file. """
        filepath = os.path.join(self.static, self.name)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        return filepath

    @property    
    def url(self):
        """ Url of the file to download via browser.
        See more at https://docs.streamlit.io/library/advanced-features/static-file-serving
        """
        return urllib.parse.urljoin("app/static/", self.name)
    
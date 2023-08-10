import os
import dotenv
import streamlit as st

from frontend.base import Container
from frontend.sidebar import Sidebar
from frontend.ner import NERTagger
from frontend.upload import Uploader
from frontend.llm import LLMRequester
from frontend.export import Exporter

## Configurations
## -----------------------------------------------------------------------------

# Set webpage title
st.set_page_config(page_title="Data Extraction Web UI")

# Global UI state
G = st.session_state

# Configurations
G.llm = 'openai'
G.debug = True

## Control flow
## -----------------------------------------------------------------------------
def main():

    st.write("# Welcome to Streamlit! 👋")

    st.sidebar.success("Select a demo above.")

    st.markdown(
        """
        Streamlit is an open-source app framework built specifically for
        Machine Learning and Data Science projects.
        **👈 Select a demo from the sidebar** to see some examples
        of what Streamlit can do!
        ### Want to learn more?
        - Check out [streamlit.io](https://streamlit.io)
        - Jump into our [documentation](https://docs.streamlit.io)
        - Ask a question in our [community
            forums](https://discuss.streamlit.io)
        ### See more complex demos
        - Use a neural net to [analyze the Udacity Self-driving Car Image
            Dataset](https://github.com/streamlit/demo-self-driving)
        - Explore a [New York City rideshare dataset](https://github.com/streamlit/demo-uber-nyc-pickups)
    """
)


if __name__ == "__main__":
    if not dotenv.load_dotenv():
        print("Warn!! No .env file found!")

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set, please check the .env file.")
        # exit(1)

    main()

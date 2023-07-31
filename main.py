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
st.set_page_config(page_title="Full Text UI")

# Global UI state
G = st.session_state

# Configurations
G.llm = 'openai'
G.debug = True

## Control flow
## -----------------------------------------------------------------------------
def main():
    side = Sidebar()

    upload = Uploader()
    upload.show()

    fetch = Container()

    split = Container()

    preprocess = Container()

    ner = NERTagger()

    embed = Container()

    prompt = Container()

    llm = LLMRequester()

    postprocess = Container()

    plot = Container()

    export = Exporter()

    commit = Container()


if __name__ == "__main__":
    if not dotenv.load_dotenv():
        print("Warn!! No .env file found!")

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set, please check the .env file.")
        # exit(1)

    main()

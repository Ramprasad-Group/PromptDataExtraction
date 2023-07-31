""" Handle API requests to OpenAI or PolyAI.

Currently only OpenAI supported. We are using Langchain to make it easy to 
switch to any different language model or API.

"""
import langchain
from langchain import PromptTemplate, LLMChain
from langchain.llms import TextGen, OpenAI

import streamlit as st
from frontend.base import Container

# Global UI state
G = st.session_state


class LLMRequester(Container):
    """ Container/div that will handle API requests to LLMs. """
    def __init__(self) -> None:
        super().__init__()

        self.polyai = "https://localhost:8001/"
        self.template = "### Human: {prompt}\n### Assistant: "

        if 'llm' not in G:
            G.llm = 'openai'
        langchain.debug = G.debug


    @st.cache_resource
    def _create_chain(self, llm):
        prompt = PromptTemplate(template=self.template,
                                input_variables=["prompt"])
        if llm == 'openai':
            llm = OpenAI()
        else:
            url = self.polyai
            llm = TextGen(model_url=url)
        return LLMChain(prompt=prompt, llm=llm)


    def make_request(self, prompt):
        """ Send an API request to the selected LLM.
        The API endpoint can be updated via G.llm.
        """
        chain = self._create_chain(G.llm)
        response = chain.run(prompt)
        return response
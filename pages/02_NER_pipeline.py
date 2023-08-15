import pylogg
import streamlit as st
from stqdm import stqdm

import frontend.resources as res
from frontend.sidebar import Sidebar
from frontend.upload import Uploader

from backend.postgres.orm import Papers, PaperSections
from backend.utils.frame import Frame
from backend.data.properties import LLMProperties

logger = pylogg.New('test')


class Sidebar:
    def __init__(self) -> None:
        self.doi = None
        self.properties = []
        self.property_df = res.selected_properties().get_list()

    def show(self):
        logger.debug("Properties: {}", self.property_df.Property)
        with st.sidebar:
           self.doi = st.text_input(label="Select paper", placeholder='doi')
           self.properties = st.multiselect(
               "Properties",
               options=self.property_df.Property)


## Control flow
## -----------------------------------------------------------------------------
def main():
    side = Sidebar()
    upload = Uploader()

    db = res.postgres()
    ner = res.materials_bert()

    text_list = []

    side.show()

    if side.doi:
        paper : Papers = Papers().get_one(
            db, criteria={'doi': side.doi}
        )
        text_list : list[PaperSections] = PaperSections().get_all(
            db, criteria={'doi': side.doi})
        
    if not text_list:
        st.info("No paragraphs found. Please enter a new DOI. Or upload a file.")
        upload.show()
    else:
        st.header(paper.title)
        st.markdown(f"https://doi.org/{side.doi}")

        selected_props = []
        for prop in side.properties:
            selected_props.append(prop)
            selected_props += res.selected_properties().get_corefs(prop)
        st.write("Looking for properties", selected_props)

        df = Frame()
        # abstract = paper.abstract

        for para in stqdm(text_list):
            st.markdown(f"[{para.type}] **{para.name}**: {para.text}")
            tags = ner.get_tags(para.text)
            tags = [tag for tag in tags if tag[1] != 'O']
            for t in tags:
                df.add(entity=t[1], text=t[0], section=para.name)

        items_found = df.df.sort_values('entity')
        st.dataframe(items_found, use_container_width=True)


if __name__ == '__main__':
    main()

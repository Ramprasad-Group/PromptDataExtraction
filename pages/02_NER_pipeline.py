import pylogg
import streamlit as st
from stqdm import stqdm

import frontend.resources as res
from frontend.sidebar import Sidebar
from frontend.ner import NERTagger

from backend.postgres.orm import Papers, PaperSections

logger = pylogg.New('test')

## Control flow
## -----------------------------------------------------------------------------
def main():
    side = Sidebar()

    db = res.postgres()
    ner = res.materials_bert()

    papers = Papers()
    paper_list : list[Papers] = papers.get_n(db, 10)

    for p in stqdm(paper_list):
        st.write(p.doi)
        st.write(p.abstract)
        tags = ner.get_tags(p.abstract)
        tags = [tag for tag in tags if tag[1] != 'O']
        st.write(tags)

    # ner = NERTagger()



if __name__ == '__main__':
    main()

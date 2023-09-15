import pylogg
import streamlit as st
from stqdm import stqdm

import matplotlib.pyplot as plt
import numpy as np

import frontend.resources as res
from frontend.sidebar import Sidebar
from frontend.upload import Uploader
from frontend.base import Container

from backend import sett
from backend.data.properties import Corefs
from backend.postgres.orm import (
    Papers, PaperTexts, ExtractedMaterials, ExtractedProperties
)

log = pylogg.New('test')
G = st.session_state


limits = {
    'Tg': (-200, 700),
    'bandgap': (0, 10),
    'HOMO': (-5, 5),
    'LUMO': (-5, 5),
    'Youngs modulus': (0, 5000),
    'Tensile strength': (10, 500),
}


class Sidebar:
    def __init__(self) -> None:
        self.doi = None
        self.properties = []

    def show(self):
        with st.sidebar:
           self.properties = st.multiselect(
               "Properties",
               options=limits.keys())

class Body(Container):
    def __init__(self) -> None:
        super().__init__()

    def top(self):
        #@Todo: does not work
        js = '''
        <script>
            var top = window.parent.document.querySelector("#header");
            top.scrollIntoView(true);
        </script>
        '''
        with self.div:
            st.components.v1.html(js)

    def show(self, db, side):
        with self.div:
            st.header("Extracted data", anchor='header')

            # Get all the data
            data = {}
            with st.spinner():
                for prop in side.properties:
                    log.trace("Fetching property data: {}", prop)
                    data[prop] = {}
                    values : list[ExtractedProperties] = []
                    for coref in Corefs[prop]:
                        values += ExtractedProperties().get_all(db, {
                            'entity_name': coref
                        })
                    
                    for val in values:
                        material : ExtractedMaterials = ExtractedMaterials().get_one(db, {
                            'id': val.material_id
                        })
                        data[prop][material.entity_name] = val.numeric_value

                    # st.write(data[prop])

                    fig, ax = plt.subplots()
                    val_list = [v for k, v in data[prop].items()
                                if v >= limits[prop][0]
                                and v <= limits[prop][1]]

                    ax.hist(val_list, bins=20)
                    ax.set(xlabel=prop, title="Extracted data for %s" %prop,
                           xlim = limits[prop])
                    st.pyplot(fig)

                if len(side.properties) > 1:
                    prop1 = side.properties[0]
                    prop2 = side.properties[1]
                    common = {}
                    for k, v1 in data[prop1].items():
                        if v1 >= limits[prop1][0] and v1 <= limits[prop1][1]:
                            if k in data[prop2]:
                                v2 = data[prop2][k]
                                if v2 >= limits[prop2][0] and v2 <= limits[prop2][1]:
                                    common[k] = (v1, v2)

                    fig, ax = plt.subplots()
                    ax.plot([v[0] for k, v in common.items()],
                            [v[1] for k, v in common.items()], 'ro')
                    ax.set(xlabel = prop1, ylabel = prop2)
                    st.pyplot(fig)

                    st.write(f"List of {prop1} and {prop2}:")
                    st.write(common)
                    




## Control flow
## -----------------------------------------------------------------------------
def main():
    side = Sidebar()
    upload = Uploader()
    body = Body()

    db = res.postgres()

    side.show()
    body.show(db, side)



if __name__ == '__main__':
    main()

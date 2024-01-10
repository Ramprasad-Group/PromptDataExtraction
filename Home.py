import streamlit as st
from backend import sett, postgres

## Configurations
## -----------------------------------------------------------------------------

# Set webpage title
st.set_page_config(page_title="Data Extraction Web UI")

import pylogg as log


## Control flow
## -----------------------------------------------------------------------------
def main():

    st.write(f"# Welcome to {sett.WebUI.header}! 👋")

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
    sett.load_settings()
    postgres.load_settings()
    log.setLevel(log.DEBUG if sett.Run.debugCount > 0 else log.INFO)

    main()

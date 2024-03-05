# Configuration file for the Sphinx documentation builder.

project     = 'Prompt-Data-Extraction'
copyright   = '2024, Akhlak Mahmood, Sonakshi Gupta'
author      = 'Akhlak Mahmood, Sonakshi Gupta'
release     = '0.1'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.githubpages',
    'sphinx.ext.autosummary',
    'myst_parser',              # pip install myst_parser
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'
html_static_path = ['_static']

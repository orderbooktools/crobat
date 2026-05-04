# -*- coding: utf-8 -*-
#
# Sphinx configuration for crobat.
# Build commands (run from docs/):
#   make html
#   make latexpdf
#   make clean && make latexpdf   # always clean before a PDF rebuild

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------

project = 'crobat'
copyright = '2024, Ivan E. Perez'
author = 'Ivan E. Perez'
version = '1.0.0'
release = '1.0.0'

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',    # NumPy / Google docstring styles
    'sphinx.ext.viewcode',    # [source] links in API pages
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'

# autodoc: show members in source order, not alphabetically
autodoc_member_order = 'bysource'

# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# ---------------------------------------------------------------------------
# LaTeX / PDF output
# ---------------------------------------------------------------------------

latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '11pt',
}

latex_documents = [
    (master_doc, 'crobat.tex', 'crobat Documentation', author, 'manual'),
]

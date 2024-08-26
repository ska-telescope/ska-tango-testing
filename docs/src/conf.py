# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
sys.path.insert(0, os.path.abspath('../../src'))


# -- Project information -----------------------------------------------------

project = 'ska-tango-testing'
copyright = '2022, CSIRO'
author = 'Drew Devereux <drew.devereux@csiro.au>'

# The full version, including alpha/beta/rc tags
release = '0.7.2'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]


autodoc_mock_imports = ["numpy", "tango", "assertpy"]


# Add any paths that contain templates here, relative to this directory.
# templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "ska_ser_sphinx_theme"

html_context = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = []


intersphinx_mapping = {
    'python': ('https://docs.python.org/3.10', None), 
    'pytest': ("https://docs.pytest.org/en/7.1.x/", None),
    "tango": ("https://pytango.readthedocs.io/en/v9.4.2/", None),
}

nitpicky = True
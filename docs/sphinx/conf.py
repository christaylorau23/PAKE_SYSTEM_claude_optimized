# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath('../../src'))

# -- Project information -----------------------------------------------------

project = 'PAKE System'
copyright = '2025, PAKE Development Team'
author = 'PAKE Development Team'

# The full version, including alpha/beta/rc tags
release = '1.0.0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
    'sphinx.ext.autosummary',
    'sphinx.ext.doctest',
    'sphinx.ext.imgmath',
    'sphinx.ext.graphviz',
    'sphinx.ext.inheritance_diagram',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
    ]
}

# -- Extension configuration -------------------------------------------------

# -- Options for autodoc extension -------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# -- Options for napoleon extension -----------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for intersphinx extension ---------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
    'pydantic': ('https://docs.pydantic.dev/', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/', None),
    'redis': ('https://redis-py.readthedocs.io/', None),
}

# -- Options for todo extension ----------------------------------------------
todo_include_todos = True

# -- Options for autosummary extension ---------------------------------------
autosummary_generate = True

# -- Options for coverage extension ------------------------------------------
coverage_show_missing_items = True
coverage_ignore_modules = []
coverage_ignore_functions = []
coverage_ignore_classes = []

# -- Options for HTML output -------------------------------------------------
html_theme_options = {
    'analytics_id': '',  # Provided by Google Analytics
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# -- Options for LaTeX output ------------------------------------------------
latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'PAKESystem.tex', 'PAKE System Documentation',
     'PAKE Development Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pakesystem', 'PAKE System Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'PAKESystem', 'PAKE System Documentation',
     author, 'PAKESystem', 'One line description of project.',
     'Miscellaneous'),
]

# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# -- Options for PDF output --------------------------------------------------
pdf_documents = [
    ('index', 'PAKESystem', 'PAKE System Documentation', 'PAKE Development Team'),
]

# -- Options for linkcheck extension -----------------------------------------
linkcheck_ignore = [
    r'http://localhost.*',
    r'https://localhost.*',
]

# -- Options for doctest extension -------------------------------------------
doctest_test_doctest_blocks = ''

# -- Options for inheritance diagram extension -------------------------------
inheritance_graph_attrs = dict(rankdir="TB", size='""')

# -- Options for graphviz extension ------------------------------------------
graphviz_output_format = 'svg'

# -- Options for imgmath extension -------------------------------------------
imgmath_image_format = 'svg'
imgmath_font_size = 14

# -- Custom configuration ----------------------------------------------------
rst_prolog = """
.. |PAKE| replace:: **PAKE System**
.. |version| replace:: 1.0.0
"""

# -- Options for autodoc extension -------------------------------------------
autodoc_mock_imports = [
    'redis',
    'asyncpg',
    'sqlalchemy',
    'fastapi',
    'pydantic',
    'structlog',
    'prometheus_client',
    'psutil',
    'opentelemetry',
    'sentry_sdk',
    'celery',
    'apscheduler',
    'dramatiq',
    'numpy',
    'pandas',
    'matplotlib',
    'seaborn',
    'plotly',
    'scikit_learn',
    'scipy',
    'statsmodels',
    'transformers',
    'sentence_transformers',
    'jinja2',
    'strawberry',
    'openpyxl',
    'xlsxwriter',
    'python_dateutil',
    'slowapi',
    'cachetools',
    'ratelimit',
    'backoff',
    'loguru',
    'rich',
    'fastapi_users',
    'gunicorn',
    'hypercorn',
    'daphne',
    'geopy',
    'pycountry',
    'hvac',
    'pytest_json_report',
    'pyyaml',
    'python_frontmatter',
    'chromadb',
    'libcst',
]

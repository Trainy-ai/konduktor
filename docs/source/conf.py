# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Konduktor"
copyright = "2024, Trainy, Inc."
author = "Andrew Aikawa"
release = "0.1.0"

html_js_files = ['js/posthog.js']

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_logo = "./images/trainy-no-background.png"
html_sidebars = {"source/**": ["sbt-sidebar-nav.html"]}
html_theme_options = {
    "show_navbar_depth": 2,
    # "show_toc_level": 2,
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "path_to_docs": "docs/source",
    "logo_only": True,
    "repository_url": "https://github.com/Trainy-ai/konduktor",
}
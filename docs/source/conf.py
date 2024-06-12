# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Konduktor"
copyright = "2024, Trainy Inc"
author = "Andrew Aikawa"
release = "0.1.0"

# -- Posthog ---------------------------------------------------
def setup(app):
    app.add_js_file(None, body="""
    <!-- PostHog tracking script -->
    <script>
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(t,o,n){function i(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}var p=e;"undefined"!=typeof n?p=e[n]=[]:n="posthog",p.people=p.people||[],p.toString=function(t){var e="posthog";return"posthog"!==n&&(e+="."+n),t||(e+=" (stub)"),e},p.people.toString=function(){return p.toString(1)+".people (stub)"},r="disable time_event track track_pageview track_links track_forms register register_once alias unregister identify clear_opt_in_out_capturing opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing reset people.set people.set_once people.unset people.increment people.append people.union people.track_charge people.clear_charges people.delete_user".split(" ");for(var c=0;c<r.length;c++)i(p,r[c]);e._i.push([t,o,n])},e.__SV=1.0,o=t.createElement("script"),o.type="text/javascript",o.async=!0,o.src="https://cdn.posthog.com/posthog.js",n=t.getElementsByTagName("script")[0],n.parentNode.insertBefore(o,n))}(document,window.posthog||[]);
    posthog.init('phc_4UgX80BfVNmYRZ2o3dJLyRMGkv1CxBozPAcPnD29uP4', {api_host: 'https://app.posthog.com'});
    </script>
    """)

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_logo = "./images/trainy.png"
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
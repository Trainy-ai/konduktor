import os
from typing import Dict

import jinja2


def fill_template(template_name: str, variables: Dict, output_path: str) -> None:
    """Create a file from a Jinja template and return the filename."""
    assert template_name.endswith(".j2"), template_name
    root_dir = os.path.dirname(os.path.dirname(__file__))
    template_path = os.path.join(root_dir, "templates", template_name)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f'Template "{template_name}" does not exist.')
    with open(template_path, "r", encoding="utf-8") as fin:
        template = fin.read()
    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write out yaml config.
    j2_template = jinja2.Template(template)
    content = j2_template.render(**variables)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(content)

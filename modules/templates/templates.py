from pathlib import Path
from jinja2 import Template


from modules.log import log


def _render_template(template_path: str, **kwargs) -> str:
    path = Path(template_path)

    if not path.exists():
        log.error(f"Template not found: {template_path}")
        return "Nothing to display."

    try:
        with path.open(mode="r", encoding="utf-8") as f:
            template = Template(f.read())
            return template.render(**kwargs)
    except Exception as e:
        log.error(f"Error while rendering template {template_path}: {e}")
        return "Nothing to display."


def render_rss_params_template(template_path: str, params_dict: dict):
    return _render_template(template_path, **params_dict)


def render_job_card_template(template_path: str, vacancy: dict):
    return _render_template(template_path, **vacancy)

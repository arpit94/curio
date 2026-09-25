"""Render markdown-authored editions into styled HTML for email delivery."""

import base64
from datetime import datetime
from functools import lru_cache
from typing import Any

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from curio.config import PROJECT_ROOT, TEMPLATES_DIR

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "htm", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


@lru_cache(maxsize=1)
def _mark_data_uri() -> str:
    """Base64-encoded PNG of the Curio mark, as a data URI.

    Inline SVG is stripped by Gmail; a base64 PNG in an <img> tag
    renders reliably across Gmail, Apple Mail, Outlook, and iOS Mail.
    """
    png = (PROJECT_ROOT / "assets" / "mark.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def markdown_to_html(md: str) -> str:
    # `nl2br` keeps line breaks the agent authored; a small custom
    # autolink pass wraps bare http(s) URLs so they become clickable.
    return md_lib.markdown(
        _autolink_bare_urls(md),
        extensions=["extra", "sane_lists", "smarty", "nl2br"],
        output_format="html5",
    )


import re as _re

_BARE_URL_RE = _re.compile(
    r"(?<![\(\[\"'>])(https?://[^\s<>\)\]]+)(?![^<]*>)"
)


def _autolink_bare_urls(md: str) -> str:
    """Wrap bare http(s) URLs in <url> so markdown emits <a> tags.

    Skips URLs already inside markdown link syntax `[..](..)` or angle brackets.
    """
    return _BARE_URL_RE.sub(r"<\1>", md)


def _pretty_date(iso: str) -> str:
    """'2026-09-25' -> '25 September'. Falls back to input on parse failure."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%-d %B")
    except ValueError:
        return iso


def render_edition_email(
    markdown_body: str,
    *,
    subject: str,
    date_str: str,
    weekday: str,
    rotation_topic: str | None = None,
) -> str:
    body_html = markdown_to_html(markdown_body)
    template = _env.get_template("edition.html.j2")
    return template.render(
        subject=subject,
        date_iso=date_str,
        date_display=_pretty_date(date_str),
        weekday=weekday,
        rotation_topic=rotation_topic or "",
        body_html=body_html,
        mark_src=_mark_data_uri(),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

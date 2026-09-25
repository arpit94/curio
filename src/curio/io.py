"""File I/O for editions and per-run logs.

Editions are markdown files with YAML frontmatter carrying structured metadata.
Logs are JSONL — one line per fetched candidate with the include/exclude decision.
"""

import json
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from curio.config import EDITIONS_DIR, LOGS_DIR


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

FM_DELIM = "---\n"


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith(FM_DELIM):
        return {}, text
    end = text.find(f"\n{FM_DELIM}", len(FM_DELIM))
    if end == -1:
        return {}, text
    fm_text = text[len(FM_DELIM) : end + 1]
    body = text[end + 1 + len(FM_DELIM) :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _serialize_frontmatter(metadata: dict[str, Any], body: str) -> str:
    fm = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
    return f"{FM_DELIM}{fm}{FM_DELIM}{body}"


# ---------------------------------------------------------------------------
# Editions
# ---------------------------------------------------------------------------

def _edition_path(when: date_cls, ext: str = "md") -> Path:
    return (
        EDITIONS_DIR
        / f"{when.year:04d}"
        / f"{when.month:02d}"
        / f"{when.day:02d}.{ext}"
    )


def write_edition_file(
    when: date_cls,
    weekday: str,
    markdown: str,
    metadata: dict[str, Any],
    *,
    rotation_topic: str = "",
) -> Path:
    """Write the day's edition as markdown-with-frontmatter, and also render
    a companion HTML file alongside for browser preview / archive."""
    md_path = _edition_path(when, "md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    full_meta = {
        "date": when.isoformat(),
        "weekday": weekday,
        **metadata,
    }
    body = markdown.lstrip("\n")
    md_path.write_text(_serialize_frontmatter(full_meta, body), encoding="utf-8")

    # Render companion HTML. Import here to avoid a circular dependency at
    # import time (render pulls in jinja2 + markdown lib).
    from curio.render import render_edition_email

    subject = f"curio · {when.isoformat()} · {weekday}"
    html = render_edition_email(
        body,
        subject=subject,
        date_str=when.isoformat(),
        weekday=weekday,
        rotation_topic=rotation_topic,
    )
    html_path = _edition_path(when, "html")
    html_path.write_text(html, encoding="utf-8")

    return md_path


def read_recent_editions(days: int) -> list[dict[str, Any]]:
    """Return up to `days` most recent editions (newest first). Each entry:
    {date, weekday, path, metadata: {...}, markdown: <body>}."""
    today = datetime.now().date()
    editions: list[dict[str, Any]] = []
    for i in range(days):
        d = today - timedelta(days=i)
        path = _edition_path(d)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        editions.append(
            {
                "date": fm.get("date", d.isoformat()),
                "weekday": fm.get("weekday"),
                "path": str(path.relative_to(EDITIONS_DIR.parent)),
                "metadata": fm,
                "markdown": body,
            }
        )
    return editions


# ---------------------------------------------------------------------------
# Run logs (JSONL)
# ---------------------------------------------------------------------------

def _log_path(when: date_cls) -> Path:
    return (
        LOGS_DIR
        / "run"
        / f"{when.year:04d}"
        / f"{when.month:02d}"
        / f"{when.day:02d}.jsonl"
    )


def append_log_entries(when: date_cls, entries: list[dict[str, Any]]) -> Path:
    path = _log_path(when)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")
    return path

"""MCP tools exposed to the Curio agent."""

import json
import logging
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

from datetime import date as date_cls, datetime

from curio import config, delivery, io as edition_io, novelty as novelty_module, render
from curio.sources import arxiv_source, comics, hackernews, quote as quote_source, wikipedia

logger = logging.getLogger(__name__)


def _ok(payload: dict) -> dict:
    """Wrap a payload in the MCP tool response envelope."""
    return {"content": [{"type": "text", "text": json.dumps(payload, default=str)}]}


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "isError": True}


# ============================================================================
# CONFIG READERS
# ============================================================================

@tool(
    "read_taste_config",
    "Load the user's taste profile — interests, anti-interests, calibration examples, novelty settings.",
    {},
)
async def read_taste_config(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok(config.load_taste())
    except Exception as e:
        logger.exception("read_taste_config failed")
        return _err(f"read_taste_config failed: {e}")


@tool(
    "read_recent_editions",
    "Return up to N most recent editions (newest first). Each edition includes date, weekday, path, metadata (from YAML frontmatter) and markdown body.",
    {"days": int},
)
async def read_recent_editions(args: dict[str, Any]) -> dict[str, Any]:
    days = args.get("days", 7)
    try:
        editions = edition_io.read_recent_editions(days=days)
        return _ok({"days_requested": days, "count": len(editions), "editions": editions})
    except Exception as e:
        logger.exception("read_recent_editions failed")
        return _err(f"read_recent_editions failed: {e}")


# ============================================================================
# SOURCE FETCHERS (stubs — return realistic-shaped dummy data)
# ============================================================================

@tool(
    "fetch_hackernews",
    "Fetch top stories from Hacker News. Returns list of {title, url, hn_url, source, points, author, comments, published_at}.",
    {"count": int},
)
async def fetch_hackernews(args: dict[str, Any]) -> dict[str, Any]:
    count = args.get("count", 15)
    try:
        items = await hackernews.fetch_top_stories(count=count)
        return _ok({"count": len(items), "items": items})
    except Exception as e:
        logger.exception("fetch_hackernews failed")
        return _err(f"fetch_hackernews failed: {e}")


@tool(
    "fetch_arxiv",
    "Fetch recent arxiv papers in the given categories. Returns list of {title, url, abstract, authors, categories, primary_category, published_at}.",
    {"categories": list, "days_back": int, "count": int},
)
async def fetch_arxiv(args: dict[str, Any]) -> dict[str, Any]:
    cats = args.get("categories", ["cs.OS", "cs.AI"])
    days_back = args.get("days_back", 2)
    count = args.get("count", 15)
    try:
        items = await arxiv_source.fetch_recent_papers(
            categories=cats, days_back=days_back, count=count
        )
        return _ok({"categories": cats, "count": len(items), "items": items})
    except Exception as e:
        logger.exception("fetch_arxiv failed")
        return _err(f"fetch_arxiv failed: {e}")


@tool(
    "fetch_quote_of_the_day",
    "Fetch a curated daily-rotating quote from ZenQuotes. Returns {quote, author, source}.",
    {},
)
async def fetch_quote_of_the_day(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok(await quote_source.fetch_quote_of_the_day())
    except Exception as e:
        logger.exception("fetch_quote_of_the_day failed")
        return _err(f"fetch_quote_of_the_day failed: {e}")


@tool(
    "fetch_wikipedia_otd",
    "Fetch Wikipedia 'On this day' — historical events, notable births/deaths, holidays, and curated 'selected' items tied to today's date.",
    {},
)
async def fetch_wikipedia_otd(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok(await wikipedia.fetch_on_this_day())
    except Exception as e:
        logger.exception("fetch_wikipedia_otd failed")
        return _err(f"fetch_wikipedia_otd failed: {e}")


@tool(
    "fetch_comic",
    "Fetch today's comic from the given source (xkcd, smbc, or oatmeal). Returns {source, title, url, image_url, alt_text}.",
    {"source": str},
)
async def fetch_comic(args: dict[str, Any]) -> dict[str, Any]:
    source = args.get("source", "xkcd")
    try:
        return _ok(await comics.fetch_comic(source))
    except Exception as e:
        logger.exception("fetch_comic failed")
        return _err(f"fetch_comic failed: {e}")


# ============================================================================
# NOVELTY
# ============================================================================

@tool(
    "compute_novelty",
    "For each candidate {title, url}, return a novelty score in [0.0, 1.0] relative to items already included in the last N days (from run logs) plus sibling candidates in this same batch. 1.0 = fully novel; 0.0 = duplicate. Uses URL normalization + rapidfuzz token-set title matching. Window and threshold are read from taste.yaml.novelty; pass window_days to override.",
    {"candidates": list, "window_days": int},
)
async def compute_novelty(args: dict[str, Any]) -> dict[str, Any]:
    candidates = args.get("candidates", [])
    try:
        taste = config.load_taste()
        novelty_cfg = taste.get("novelty", {}) or {}
        window_days = args.get("window_days") or novelty_cfg.get("window_days", 7)
        threshold = novelty_cfg.get("title_similarity_threshold", 85)
        scores = novelty_module.compute_novelty_scores(
            candidates, window_days=window_days, title_threshold=threshold
        )
        return _ok(
            {"scores": scores, "window_days": window_days, "threshold": threshold}
        )
    except Exception as e:
        logger.exception("compute_novelty failed")
        return _err(f"compute_novelty failed: {e}")


# ============================================================================
# WRITERS + DELIVERY
# ============================================================================

@tool(
    "write_edition",
    "Persist the day's edition to editions/YYYY/MM/DD.md (markdown with YAML frontmatter) and also renders a styled companion HTML at editions/YYYY/MM/DD.html for browser preview. Overwrites any existing files for the same date. Pass rotation_topic so the header renders correctly.",
    {
        "date": str,
        "weekday": str,
        "markdown": str,
        "metadata": dict,
        "rotation_topic": str,
    },
)
async def write_edition(args: dict[str, Any]) -> dict[str, Any]:
    date_str = args.get("date", "")
    weekday = args.get("weekday", "")
    markdown = args.get("markdown", "")
    metadata = args.get("metadata", {}) or {}
    rotation_topic = args.get("rotation_topic", "")
    try:
        when = datetime.strptime(date_str, "%Y-%m-%d").date()
        path = edition_io.write_edition_file(
            when, weekday, markdown, metadata, rotation_topic=rotation_topic
        )
        logger.info(f"write_edition({date_str}): {len(markdown)} chars → {path}")
        return _ok(
            {
                "date": date_str,
                "chars": len(markdown),
                "path": str(path),
                "html_path": str(path.with_suffix(".html")),
            }
        )
    except Exception as e:
        logger.exception("write_edition failed")
        return _err(f"write_edition failed: {e}")


@tool(
    "write_log",
    "Append per-run reasoning log to logs/run/YYYY/MM/DD.jsonl. Entries is a list of dicts (one per candidate) — expected keys: title, url, source, included (bool), category, reason. Appends (does not overwrite) so repeated runs on the same day accumulate.",
    {"date": str, "entries": list},
)
async def write_log(args: dict[str, Any]) -> dict[str, Any]:
    date_str = args.get("date", "")
    entries = args.get("entries", []) or []
    try:
        when = datetime.strptime(date_str, "%Y-%m-%d").date()
        path = edition_io.append_log_entries(when, entries)
        logger.info(f"write_log({date_str}): {len(entries)} entries → {path}")
        return _ok({"date": date_str, "entry_count": len(entries), "path": str(path)})
    except Exception as e:
        logger.exception("write_log failed")
        return _err(f"write_log failed: {e}")


@tool(
    "send_email",
    "Send the day's digest via Resend. You supply subject, markdown_body (the edition markdown you assembled), plus date/weekday/rotation_topic for header rendering. HTML wrapping is done server-side. Honors CURIO_DRY_RUN=1 as a no-op returning {sent: false, dry_run: true}.",
    {
        "subject": str,
        "markdown_body": str,
        "date": str,
        "weekday": str,
        "rotation_topic": str,
    },
)
async def send_email(args: dict[str, Any]) -> dict[str, Any]:
    subject = args.get("subject", "")
    markdown_body = args.get("markdown_body", "")
    date_str = args.get("date", "")
    weekday = args.get("weekday", "")
    rotation_topic = args.get("rotation_topic", "")
    try:
        html_body = render.render_edition_email(
            markdown_body,
            subject=subject,
            date_str=date_str,
            weekday=weekday,
            rotation_topic=rotation_topic,
        )
        result = await delivery.send_digest(subject, html_body, markdown_body)
        result.setdefault("html_chars", len(html_body))
        logger.info(f"send_email: {result}")
        return _ok(result)
    except Exception as e:
        logger.exception("send_email failed")
        return _err(f"send_email failed: {e}")


# ============================================================================
# MCP SERVER FACTORY
# ============================================================================

def create_curio_mcp_server():
    """Create the MCP server exposing all curio tools."""
    return create_sdk_mcp_server(
        name="curio-tools",
        version="0.1.0",
        tools=[
            read_taste_config,
            read_recent_editions,
            fetch_hackernews,
            fetch_arxiv,
            fetch_quote_of_the_day,
            fetch_wikipedia_otd,
            fetch_comic,
            compute_novelty,
            write_edition,
            write_log,
            send_email,
        ],
    )

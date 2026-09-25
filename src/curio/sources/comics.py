"""Comic fetchers: XKCD (JSON API), SMBC & The Oatmeal (RSS)."""

import asyncio
from typing import Any

import feedparser
import httpx

XKCD_LATEST = "https://xkcd.com/info.0.json"
SMBC_RSS = "https://www.smbc-comics.com/comic/rss"
OATMEAL_RSS = "https://feeds.feedburner.com/oatmealfeed"


async def _fetch_xkcd() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(XKCD_LATEST)
        r.raise_for_status()
        data = r.json()
    return {
        "source": "xkcd",
        "title": data.get("safe_title") or data.get("title", ""),
        "url": f"https://xkcd.com/{data['num']}/",
        "image_url": data.get("img", ""),
        "alt_text": data.get("alt", ""),
        "number": data.get("num"),
    }


def _rss_first(url: str, source_name: str) -> dict[str, Any]:
    feed = feedparser.parse(url)
    if not feed.entries:
        return {
            "source": source_name,
            "title": "",
            "url": "",
            "image_url": "",
            "alt_text": "",
        }
    e = feed.entries[0]
    image_url = ""
    if getattr(e, "media_content", None):
        image_url = e.media_content[0].get("url", "")
    elif getattr(e, "links", None):
        for link in e.links:
            if "image" in link.get("type", ""):
                image_url = link.get("href", "")
                break
    return {
        "source": source_name,
        "title": e.get("title", ""),
        "url": e.get("link", ""),
        "image_url": image_url,
        "alt_text": e.get("summary", "")[:200],
    }


async def _fetch_smbc() -> dict[str, Any]:
    return await asyncio.to_thread(_rss_first, SMBC_RSS, "smbc")


async def _fetch_oatmeal() -> dict[str, Any]:
    return await asyncio.to_thread(_rss_first, OATMEAL_RSS, "oatmeal")


async def fetch_comic(source: str) -> dict[str, Any]:
    source = source.lower().strip()
    if source == "xkcd":
        return await _fetch_xkcd()
    if source == "smbc":
        return await _fetch_smbc()
    if source in ("oatmeal", "theoatmeal"):
        return await _fetch_oatmeal()
    raise ValueError(f"Unknown comic source: {source!r}")

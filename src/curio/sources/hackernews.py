"""Hacker News top stories via the Firebase API."""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

API_BASE = "https://hacker-news.firebaseio.com/v0"


async def fetch_top_stories(count: int = 15) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{API_BASE}/topstories.json")
        r.raise_for_status()
        ids: list[int] = r.json()[:count]

        item_responses = await asyncio.gather(
            *(client.get(f"{API_BASE}/item/{i}.json") for i in ids),
            return_exceptions=True,
        )

    items: list[dict[str, Any]] = []
    for resp in item_responses:
        if isinstance(resp, Exception):
            continue
        try:
            item = resp.json()
        except Exception:
            continue
        if not item or item.get("dead") or item.get("deleted"):
            continue
        hn_url = f"https://news.ycombinator.com/item?id={item['id']}"
        items.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url") or hn_url,
                "hn_url": hn_url,
                "source": "hackernews",
                "points": item.get("score", 0),
                "author": item.get("by", ""),
                "comments": item.get("descendants", 0),
                "published_at": datetime.fromtimestamp(
                    item.get("time", 0), tz=timezone.utc
                ).isoformat(),
            }
        )
    return items

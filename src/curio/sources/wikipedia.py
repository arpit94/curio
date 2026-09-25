"""Wikipedia 'On this day' via Wikimedia REST API."""

from datetime import datetime
from typing import Any

import httpx

BASE = "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all"
USER_AGENT = "curio/0.1 (personal daily digest)"


def _shape(items: list[dict]) -> list[dict[str, Any]]:
    shaped = []
    for it in items or []:
        page = (it.get("pages") or [{}])[0]
        shaped.append(
            {
                "year": it.get("year"),
                "text": it.get("text"),
                "page_title": page.get("titles", {}).get("normalized"),
                "page_url": (page.get("content_urls", {}).get("desktop") or {}).get(
                    "page"
                ),
            }
        )
    return shaped


async def fetch_on_this_day(when: datetime | None = None) -> dict[str, Any]:
    when = when or datetime.now()
    month = when.strftime("%m")
    day = when.strftime("%d")
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        r = await client.get(f"{BASE}/{month}/{day}")
        r.raise_for_status()
        data = r.json()

    return {
        "date": when.strftime("%B %d"),
        "events": _shape(data.get("events", [])),
        "births": _shape(data.get("births", [])),
        "deaths": _shape(data.get("deaths", [])),
        "holidays": _shape(data.get("holidays", [])),
        "selected": _shape(data.get("selected", [])),
    }

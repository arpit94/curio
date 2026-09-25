"""Daily quote via the ZenQuotes API — free, no auth, rotates once per day."""

from typing import Any

import httpx

TODAY_URL = "https://zenquotes.io/api/today"


async def fetch_quote_of_the_day() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(TODAY_URL)
        r.raise_for_status()
        data = r.json()
    if not data:
        return {"quote": "", "author": "", "source": "zenquotes"}
    q = data[0]
    return {
        "quote": q.get("q", "").strip(),
        "author": q.get("a", "").strip(),
        "source": "zenquotes",
    }

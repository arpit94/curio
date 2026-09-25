"""arxiv paper search via the `arxiv` Python client."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import arxiv


def _search_sync(categories: list[str], days_back: int, count: int) -> list[dict[str, Any]]:
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    search = arxiv.Search(
        query=cat_query,
        max_results=count * 3,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    items: list[dict[str, Any]] = []
    client = arxiv.Client()
    for r in client.results(search):
        if r.published < cutoff:
            continue
        items.append(
            {
                "title": r.title.strip(),
                "url": r.entry_id,
                "abstract": r.summary.strip(),
                "authors": [a.name for a in r.authors],
                "categories": r.categories,
                "primary_category": r.primary_category,
                "published_at": r.published.isoformat(),
                "source": "arxiv",
            }
        )
        if len(items) >= count:
            break
    return items


async def fetch_recent_papers(
    categories: list[str], days_back: int = 2, count: int = 15
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_search_sync, categories, days_back, count)

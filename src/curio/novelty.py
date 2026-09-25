"""Novelty scoring — compare candidates against items included in the last N editions.

Strategy: exact-URL match (after normalization) → novelty 0.0; otherwise best fuzzy
title-similarity (rapidfuzz token_set_ratio) mapped to novelty via 1 - score/100.
Similarity above the threshold is flagged as a probable duplicate.

History is drawn from the JSONL logs written by `write_log` — items with
`included: True` from the last `window_days`. Also compares against sibling
candidates in the same fetch (catches "same story from 4 sources").
"""

import json
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from rapidfuzz import fuzz, process

from curio.config import LOGS_DIR


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url.lower().strip())
    host = p.netloc.replace("www.", "")
    path = p.path.rstrip("/")
    query = f"?{p.query}" if p.query else ""
    return f"{host}{path}{query}"


def _load_recent_included(window_days: int) -> list[dict[str, str]]:
    today = datetime.now().date()
    items: list[dict[str, str]] = []
    for i in range(window_days):
        d = today - timedelta(days=i)
        log_path = (
            LOGS_DIR / "run" / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}.jsonl"
        )
        if not log_path.exists():
            continue
        with log_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("included"):
                    items.append(
                        {
                            "title": entry.get("title", ""),
                            "url": entry.get("url", ""),
                        }
                    )
    return items


def compute_novelty_scores(
    candidates: list[dict[str, Any]],
    window_days: int = 7,
    title_threshold: int = 85,
) -> list[dict[str, Any]]:
    """Score each candidate's novelty in [0.0, 1.0]. 1.0 = fully novel; 0.0 = duplicate."""
    historical = _load_recent_included(window_days)
    hist_url_set = {_normalize_url(h["url"]) for h in historical if h.get("url")}
    hist_titles = [h["title"] for h in historical if h.get("title")]

    results: list[dict[str, Any]] = []
    for i, c in enumerate(candidates):
        c_title = c.get("title", "")
        c_url = c.get("url", "")
        c_norm = _normalize_url(c_url)

        if c_norm and c_norm in hist_url_set:
            results.append(
                {
                    "url": c_url,
                    "title": c_title,
                    "novelty_score": 0.0,
                    "reason": "exact URL match in recent history",
                }
            )
            continue

        sibling_titles = [
            candidates[j].get("title", "")
            for j in range(len(candidates))
            if j != i and candidates[j].get("title")
        ]
        comparators = hist_titles + sibling_titles
        if not comparators or not c_title:
            results.append({"url": c_url, "title": c_title, "novelty_score": 1.0})
            continue

        match = process.extractOne(c_title, comparators, scorer=fuzz.token_set_ratio)
        if match is None:
            results.append({"url": c_url, "title": c_title, "novelty_score": 1.0})
            continue

        _, score, _ = match
        novelty = max(0.0, 1.0 - (score / 100.0))
        entry: dict[str, Any] = {
            "url": c_url,
            "title": c_title,
            "novelty_score": round(novelty, 3),
            "similarity_score": round(score, 1),
        }
        if score >= title_threshold:
            entry["reason"] = f"title {score:.0f}% similar to a recent item"
        results.append(entry)
    return results

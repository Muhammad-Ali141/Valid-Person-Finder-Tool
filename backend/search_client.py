import time
import logging
import warnings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*renamed.*ddgs.*")

RATE_LIMIT_DELAY = 1.0
MAX_RESULTS_PER_QUERY = 8


def _normalize_result(r: dict) -> dict:
    return {
        "title": r.get("title", "") or "",
        "href": r.get("href", r.get("url", r.get("link", ""))) or "",
        "body": r.get("body", r.get("snippet", "")) or "",
    }


def _ddg_search(query: str) -> List[Dict[str, Any]]:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=MAX_RESULTS_PER_QUERY))
        return [_normalize_result(r) for r in results]
    except Exception as e:
        logger.warning("DuckDuckGo search failed for %s: %s", query, e)
        return []


def search_multiple_queries(queries: List[str]) -> List[Dict[str, Any]]:
    seen_urls = set()
    combined = []
    for i, q in enumerate(queries):
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY)
        items = _ddg_search(q)
        for item in items:
            url = (item.get("href") or "").strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                combined.append(item)
    return combined

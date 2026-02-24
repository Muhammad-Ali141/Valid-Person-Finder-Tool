import time
import logging
from typing import List, Dict, Any

from backend.query_builder import build_queries
from backend.search_client import search_multiple_queries
from backend.extractor import extract_from_snippet, extract_from_page

logger = logging.getLogger(__name__)

CREDIBLE_DOMAINS = ("linkedin.com", "wikipedia.org", "crunchbase.com", "bloomberg.com", "reuters.com", "forbes.com")
SNIPPET_DELAY = 0.5
PAGE_FETCH_DELAY = 1.0


def _source_credibility_score(url: str) -> int:
    url_lower = url.lower()
    for i, d in enumerate(CREDIBLE_DOMAINS):
        if d in url_lower:
            return 10 - i
    return 0


def _normalize_name(first: str, last: str) -> str:
    return f"{(first or '').strip()} {(last or '').strip()}".strip().lower()


def run_pipeline(company: str, designation: str) -> Dict[str, Any]:
    company = (company or "").strip()
    designation = (designation or "").strip()
    empty_result = {
        "first_name": "",
        "last_name": "",
        "current_title": designation,
        "source_url": "",
        "confidence_score": 0.0,
        "sources_checked": [],
        "found": False,
        "error": None,
    }
    if not company or not designation:
        empty_result["error"] = "Company and designation are required"
        return empty_result
    try:
        queries = build_queries(company, designation)
        if not queries:
            empty_result["error"] = "Could not build search queries"
            return empty_result
        results = search_multiple_queries(queries)
        if not results:
            empty_result["error"] = "No search results found"
            return empty_result
        extractions: List[Dict[str, Any]] = []
        sources_checked = []
        for item in results:
            url = (item.get("href") or "").strip()
            if not url or url in sources_checked:
                continue
            title = item.get("title") or ""
            body = item.get("body") or ""
            time.sleep(SNIPPET_DELAY)
            out = extract_from_snippet(company, designation, title, body, url)
            sources_checked.append(url)
            if out:
                extractions.append(out)
                if len(extractions) >= 3:
                    break
        for item in results:
            if len(extractions) >= 3:
                break
            url = (item.get("href") or "").strip()
            if not url or url in sources_checked:
                continue
            if any(e.get("source_url") == url for e in extractions):
                continue
            time.sleep(PAGE_FETCH_DELAY)
            out = extract_from_page(company, designation, url)
            sources_checked.append(url)
            if out:
                extractions.append(out)
        if not extractions:
            empty_result["current_title"] = designation
            empty_result["sources_checked"] = sources_checked
            empty_result["error"] = "Could not extract a name from any source"
            return empty_result
        name_counts: Dict[str, List[Dict]] = {}
        for e in extractions:
            key = _normalize_name(e.get("first_name", ""), e.get("last_name", ""))
            if key and len(key) > 1:
                name_counts.setdefault(key, []).append(e)
        best_key = None
        best_count = 0
        for k, arr in name_counts.items():
            if len(arr) > best_count:
                best_count = len(arr)
                best_key = k
        if not best_key:
            chosen = extractions[0]
        else:
            candidates = name_counts[best_key]
            chosen = max(candidates, key=lambda x: _source_credibility_score(x.get("source_url", "")))
        n_agree = len(name_counts.get(best_key, []))
        if n_agree >= 2:
            confidence = min(0.95, 0.6 + 0.15 * n_agree)
        else:
            confidence = 0.5
        return {
            "first_name": chosen.get("first_name", ""),
            "last_name": chosen.get("last_name", ""),
            "current_title": designation,
            "source_url": chosen.get("source_url", ""),
            "confidence_score": round(confidence, 2),
            "sources_checked": sources_checked,
            "found": True,
            "error": None,
        }
    except Exception as e:
        logger.exception("Pipeline error")
        empty_result["error"] = str(e)
        return empty_result

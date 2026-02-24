import os
import re
import logging
from typing import Optional, Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.5",
}

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"


def fetch_page_text(url: str, max_chars: int = 12000) -> str:
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars] if text else ""
    except Exception as e:
        logger.warning("Fetch failed for %s: %s", url, e)
        return ""


def extract_name_with_groq(
    company: str,
    designation: str,
    text: str,
    source_hint: str = "",
) -> Optional[Tuple[str, str]]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set")
        return None
    if not text or len(text.strip()) < 20:
        return None
    prompt = f"""You are given text that may mention a person who holds a specific role at a company.
Company: {company}
Role/Designation: {designation}
Source context: {source_hint or "web search result"}

Extract the full name of the person who holds this role at this company. Reply with exactly two words: first name and last name, separated by a space. If you cannot find a clear full name, reply with: NONE"""
    user_content = f"Text to analyze:\n\n{text[:8000]}"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You extract person names. Reply only with 'FirstName LastName' or 'NONE'."},
                {"role": "user", "content": prompt + "\n\n" + user_content},
            ],
            max_tokens=50,
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content or content.upper() == "NONE":
            return None
        parts = content.split()
        if len(parts) >= 2:
            return (parts[0], " ".join(parts[1:]))
        if len(parts) == 1 and len(parts[0]) > 1:
            return (parts[0], "")
        return None
    except Exception as e:
        logger.warning("Groq extraction failed: %s", e)
        return None


def extract_from_snippet(
    company: str,
    designation: str,
    title: str,
    body: str,
    url: str,
) -> Optional[Dict[str, Any]]:
    text = f"{title}\n{body}".strip()
    if not text:
        return None
    name = extract_name_with_groq(company, designation, text, source_hint=url)
    if name:
        return {
            "first_name": name[0],
            "last_name": name[1] or "",
            "source_url": url,
            "from_snippet": True,
        }
    return None


def extract_from_page(
    company: str,
    designation: str,
    url: str,
) -> Optional[Dict[str, Any]]:
    text = fetch_page_text(url)
    if not text:
        return None
    name = extract_name_with_groq(company, designation, text, source_hint=url)
    if name:
        return {
            "first_name": name[0],
            "last_name": name[1] or "",
            "source_url": url,
            "from_snippet": False,
        }
    return None

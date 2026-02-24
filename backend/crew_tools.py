from typing import Type, Optional

from pydantic import BaseModel, Field


def _search_impl(company: str, designation: str, refined_query: Optional[str] = None) -> str:
    from backend.query_builder import build_queries
    from backend.search_client import search_multiple_queries
    if refined_query and refined_query.strip():
        queries = [refined_query.strip()]
    else:
        queries = build_queries(company, designation)
    if not queries:
        return "Error: Could not build search queries."
    results = search_multiple_queries(queries)
    if not results:
        return "No search results found. Try a refined query or different terms."
    lines = []
    for i, r in enumerate(results[:12], 1):
        title = (r.get("title") or "").strip() or "(no title)"
        href = (r.get("href") or "").strip()
        body = (r.get("body") or "").strip()[:300]
        lines.append(f"[{i}] Title: {title}\nURL: {href}\nSnippet: {body}")
    return "\n\n".join(lines)


def _extract_impl(company: str, designation: str, text: str, source_url: str = "") -> str:
    from backend.extractor import extract_name_with_groq
    if not text or len(text.strip()) < 10:
        return "NONE"
    result = extract_name_with_groq(company, designation, text, source_hint=source_url)
    if result:
        return f"{result[0]} {result[1]}".strip()
    return "NONE"


try:
    from crewai.tools import BaseTool
    _HAS_CREWAI = True
except ImportError:
    _HAS_CREWAI = False
    BaseTool = object


if _HAS_CREWAI:

    class PersonSearchInput(BaseModel):
        company: str = Field(..., description="Company or organization name")
        designation: str = Field(..., description="Job title or role, e.g. CEO, Founder")
        refined_query: Optional[str] = Field(default=None, description="Optional alternate search query")

    class PersonSearchTool(BaseTool):
        name: str = "person_search"
        description: str = "Search the web for the person who holds a given role at a company. Returns title, URL, snippet per result. Use refined_query to try another query if results are weak."
        args_schema: Type[BaseModel] = PersonSearchInput

        def _run(self, company: str, designation: str, refined_query: Optional[str] = None) -> str:
            return _search_impl(company, designation, refined_query)

    class ExtractNameInput(BaseModel):
        company: str = Field(..., description="Company name")
        designation: str = Field(..., description="Role or title")
        text: str = Field(..., description="Snippet or page text that may mention the person")
        source_url: str = Field(default="", description="URL of the source")

    class ExtractNameFromTextTool(BaseTool):
        name: str = "extract_name_from_text"
        description: str = "Extract the full name (first and last) of the person in the given role at the company from the text. Returns 'FirstName LastName' or 'NONE'."
        args_schema: Type[BaseModel] = ExtractNameInput

        def _run(self, company: str, designation: str, text: str, source_url: str = "") -> str:
            return _extract_impl(company, designation, text, source_url)

else:
    PersonSearchTool = None
    ExtractNameFromTextTool = None

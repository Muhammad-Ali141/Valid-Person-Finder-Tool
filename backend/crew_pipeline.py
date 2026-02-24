import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from crewai import Agent, Task, Crew, Process, LLM
except ImportError:
    Agent = Task = Crew = Process = LLM = None

from backend.crew_tools import PersonSearchTool, ExtractNameFromTextTool


def _make_crew(company: str, designation: str):
    if not all([Agent, Task, Crew, Process, LLM]):
        raise RuntimeError("CrewAI not installed. pip install crewai")
    tools = []
    if PersonSearchTool is not None:
        tools.append(PersonSearchTool())
    if ExtractNameFromTextTool is not None:
        tools.append(ExtractNameFromTextTool())
    llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.2)
    researcher = Agent(
        role="Researcher",
        goal="Find the full name of the person who holds a specific role at a given company by searching the web and extracting names from search results.",
        backstory="You are an expert at gathering information from public sources. You use search to find relevant pages, then extract the person's name from snippets. If the first search returns weak or irrelevant results, you refine the query (e.g. add 'LinkedIn' or rephrase) and search again.",
        llm=llm,
        tools=tools,
        verbose=True,
        allow_delegation=False,
    )
    validator = Agent(
        role="Validator",
        goal="Cross-validate the extracted name across multiple sources and assign a confidence score (0.0 to 1.0).",
        backstory="You receive the Researcher's findings: multiple sources with candidate names. You determine which name appears in more than one source, pick the most credible source, and assign high confidence when multiple sources agree, lower when only one source.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
    reporter = Agent(
        role="Reporter",
        goal="Produce the final structured result as a single JSON object.",
        backstory="You turn the Validator's conclusion into a strict JSON object with keys: first_name, last_name, current_title, source_url, confidence_score. No extra text, only valid JSON.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
    research_task = Task(
        description=f"""Search for the person who holds the role "{designation}" at the company "{company}".
Use the person_search tool with company="{company}" and designation="{designation}".
For each search result (title, URL, snippet), use extract_name_from_text to get the person's name from that snippet.
If the first search gives few or irrelevant results, use person_search again with refined_query set to something like "{company} {designation} LinkedIn" or "{company} CEO name".
Produce a clear summary: for each source URL, list the name extracted (or NONE). Example format:
- Source: [URL1] -> Name: John Doe
- Source: [URL2] -> Name: John Doe
- Source: [URL3] -> Name: NONE
List all sources you checked and the name (or NONE) for each.""",
        expected_output="A summary listing each source URL and the full name extracted from that source (or NONE). If you refined the query and searched again, mention that.",
        agent=researcher,
    )
    validation_task = Task(
        description="""You receive the Researcher's summary: multiple sources with extracted names.
Decide which person name is correct (the one that appears in multiple sources, or the one from the most credible source if only one).
Assign a confidence_score between 0.0 and 1.0: use 0.7-0.95 when the same name appears in 2+ sources, 0.5-0.6 when only one source.
Pick one source_url as the primary source (prefer linkedin.com, wikipedia.org, company official sites, then news).
Output: the chosen first_name, last_name, source_url, and confidence_score.""",
        expected_output="The verified first name, last name, primary source URL, and confidence score (0.0-1.0). Short paragraph or bullet points.",
        agent=validator,
        context=[research_task],
    )
    reporting_task = Task(
        description="""Turn the Validator's output into a single JSON object. Use exactly these keys:
- first_name (string)
- last_name (string)
- current_title (string): the designation, e.g. """ + designation + """
- source_url (string)
- confidence_score (number between 0 and 1)
If no person was found, use first_name: "", last_name: "", confidence_score: 0.
Output ONLY the JSON object, no markdown code block, no explanation.""",
        expected_output="A single line or block of valid JSON with keys first_name, last_name, current_title, source_url, confidence_score.",
        agent=reporter,
        context=[validation_task],
    )
    return Crew(
        agents=[researcher, validator, reporter],
        tasks=[research_task, validation_task, reporting_task],
        process=Process.sequential,
        verbose=True,
    )


def _extract_json_block(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def _parse_reporter_output(text: str, designation: str) -> Dict[str, Any]:
    empty = {
        "first_name": "",
        "last_name": "",
        "current_title": designation,
        "source_url": "",
        "confidence_score": 0.0,
        "sources_checked": [],
        "found": False,
        "error": None,
    }
    if not text or not text.strip():
        return empty
    text = text.strip()
    if "```" in text:
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
    json_str = _extract_json_block(text)
    if not json_str:
        return empty
    try:
        data = json.loads(json_str)
        first = (data.get("first_name") or "").strip()
        last = (data.get("last_name") or "").strip()
        found = bool(first or last)
        return {
            "first_name": first,
            "last_name": last,
            "current_title": (data.get("current_title") or designation).strip(),
            "source_url": (data.get("source_url") or "").strip(),
            "confidence_score": min(1.0, max(0.0, float(data.get("confidence_score", 0)))),
            "sources_checked": data.get("sources_checked", []) if isinstance(data.get("sources_checked"), list) else [],
            "found": found,
            "error": None,
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("Failed to parse Reporter JSON: %s", e)
        return empty


def run_crew_pipeline(company: str, designation: str) -> Dict[str, Any]:
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
        crew = _make_crew(company, designation)
        result = crew.kickoff()
        output = str(result)
        if hasattr(result, "raw") and result.raw:
            output = str(result.raw)
        if hasattr(result, "tasks_output") and result.tasks_output:
            last_out = result.tasks_output[-1]
            output = last_out if isinstance(last_out, str) else str(last_out)
        parsed = _parse_reporter_output(output, designation)
        if not parsed.get("sources_checked"):
            parsed["sources_checked"] = []
        return parsed
    except Exception as e:
        logger.exception("Crew pipeline error")
        empty_result["error"] = str(e)
        return empty_result

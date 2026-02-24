from typing import List

DESIGNATION_ALIASES = {
    "ceo": "Chief Executive Officer",
    "cfo": "Chief Financial Officer",
    "cto": "Chief Technology Officer",
    "coo": "Chief Operating Officer",
    "cmo": "Chief Marketing Officer",
    "co-founder": "Co-Founder",
    "cofounder": "Co-Founder",
    "founder": "Founder",
    "director": "Director",
    "manager": "Manager",
    "head": "Head",
    "vp": "Vice President",
    "vice president": "Vice President",
    "svp": "Senior Vice President",
    "evp": "Executive Vice President",
    "md": "Managing Director",
    "managing director": "Managing Director",
    "owner": "Owner",
    "partner": "Partner",
    "lead": "Lead",
    "chief": "Chief",
}


def normalize_designation(designation: str) -> str:
    if not designation or not designation.strip():
        return ""
    d = designation.strip()
    d_lower = d.lower()
    expanded = DESIGNATION_ALIASES.get(d_lower)
    if expanded and expanded != d:
        return expanded
    return d


def build_queries(company: str, designation: str) -> List[str]:
    company = (company or "").strip()
    designation = (designation or "").strip()
    if not company or not designation:
        return []
    normalized = normalize_designation(designation)
    variants = list({designation, normalized})
    queries = []
    for d in variants[:2]:
        q = f"{company} {d} name"
        if q not in queries:
            queries.append(q)
    q2 = f"who is {designation} of {company}"
    if q2 not in queries:
        queries.append(q2)
    q3 = f"{company} {designation} LinkedIn"
    if q3 not in queries and len(queries) < 4:
        queries.append(q3)
    return queries[:2] if len(queries) < 2 else queries[:3]

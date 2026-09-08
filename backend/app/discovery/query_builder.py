# app/discovery/query_builder.py

from app.processing.query_parser import ParsedQuery

def build_search_queries(query: ParsedQuery) -> list[str]:
    """
    Generate multiple search query strings from a ParsedQuery.
    More variety = more sources found = better coverage.
    """
    parts = []

    country  = query.country  or ""
    industry = query.industry or ""
    city     = query.city     or ""

    emp_str = ""
    if query.employee_min and query.employee_max:
        emp_str = f"{query.employee_min}-{query.employee_max} employees"
    elif query.employee_max:
        emp_str = f"under {query.employee_max} employees"
    elif query.employee_min:
        emp_str = f"over {query.employee_min} employees"

    loc = city or country

    # Core queries — broad to specific
    base_queries = [
        f"{loc} {industry} companies",
        f"{loc} {industry} startups",
        f"{loc} {industry} software companies",
        f"{country} {industry} companies {emp_str}",
        f"{industry} startups {loc}",
        f"top {industry} companies in {loc}",
        f"best {industry} startups {loc}",
        f"list of {industry} companies {country}",
        f"{loc} tech startups {industry}",
        f"site:crunchbase.com {loc} {industry}",
        f"site:tracxn.com {loc} {industry}",
        f"site:g2.com {industry} companies",
        f"site:clutch.co {loc} {industry}",
        f"site:linkedin.com/company {loc} {industry}",
    ]

    # Remove blanks from queries with missing fields
    return [" ".join(q.split()) for q in base_queries if q.strip()]
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedQuery:
    country:      Optional[str] = None
    city:         Optional[str] = None
    industry:     Optional[str] = None
    employee_min: Optional[int] = None
    employee_max: Optional[int] = None

COUNTRY_MAP = {
    "indian": "India", "india": "India",
    "american": "USA", "us": "USA", "usa": "USA",
    "uk": "UK", "british": "UK",
    "singapore": "Singapore", "singaporean": "Singapore",
}

INDUSTRY_KEYWORDS = [
    "SaaS", "Fintech", "EdTech", "HealthTech",
    "AI", "E-commerce", "Logistics", "HRTech",
]

CITY_KEYWORDS = [
    "Bangalore", "Bengaluru", "Chennai", "Mumbai",
    "Delhi", "Hyderabad", "Pune", "Kolkata",
]

def parse_query(query: str) -> ParsedQuery:
    result = ParsedQuery()
    text = query.lower()

    # --- employee range ---
    # handles: "10-100", "10 to 100", "10–100"
    match = re.search(r'(\d+)\s*(?:-|to|–)\s*(\d+)\s*employees?', text)
    if match:
        result.employee_min = int(match.group(1))
        result.employee_max = int(match.group(2))

    # handles: "fewer than 50", "less than 50", "under 50"
    match = re.search(r'(?:fewer than|less than|under)\s*(\d+)\s*employees?', text)
    if match:
        result.employee_max = int(match.group(1))

    # handles: "more than 50", "over 50", "at least 50"
    match = re.search(r'(?:more than|over|at least)\s*(\d+)\s*employees?', text)
    if match:
        result.employee_min = int(match.group(1))

    # --- country ---
    for keyword, country in COUNTRY_MAP.items():
        if keyword in text:
            result.country = country
            break

    # --- industry ---
    for industry in INDUSTRY_KEYWORDS:
        if industry.lower() in text:
            result.industry = industry
            break

    # --- city ---
    for city in CITY_KEYWORDS:
        if city.lower() in text:
            result.city = city
            break
        # handle "bengaluru" -> "Bangalore"
        if city.lower() == "bangalore" and "bengaluru" in text:
            result.city = "Bangalore"

    return result
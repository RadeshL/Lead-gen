# app/enrichment/base.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class EnrichmentResult:
    """
    What one enrichment source found.
    Only fields that were actually found are set — None means not found.
    Every field also carries a source tag and confidence score so the DB
    can store provenance (which source said what).
    """
    source: str                          # "linkedin", "glassdoor", "clearbit"

    name:          Optional[str]  = None
    description:   Optional[str]  = None
    country:       Optional[str]  = None
    city:          Optional[str]  = None
    employee_min:  Optional[int]  = None
    employee_max:  Optional[int]  = None
    employee_range: Optional[str] = None
    industry:      Optional[str]  = None
    founded_year:  Optional[int]  = None
    linkedin_url:  Optional[str]  = None
    confidence:    float          = 0.8  # how much to trust this source
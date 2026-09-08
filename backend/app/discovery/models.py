# app/discovery/models.py

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CandidateCompany:
    url: str                              # always required
    name: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    employee_range: Optional[str] = None  # raw string e.g. "11-50"
    linkedin_url: Optional[str] = None
    source: str = "unknown"               # which provider found this

    def domain(self) -> str:
        """Normalised domain — used as deduplication key."""
        from urllib.parse import urlparse
        host = urlparse(self.url).netloc or self.url
        return host.lower().removeprefix("www.")
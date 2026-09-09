# app/scraping/base.py

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ScrapedData:
    # Source
    url: str
    source_name: Optional[str] = None   # name hint from discovery

    # Core fields
    name:         Optional[str] = None
    description:  Optional[str] = None
    tagline:      Optional[str] = None

    # Location
    country:      Optional[str] = None
    city:         Optional[str] = None
    address:      Optional[str] = None

    # Size
    employee_range: Optional[str] = None   # raw e.g. "11-50 employees"
    employee_min:   Optional[int] = None
    employee_max:   Optional[int] = None

    # Classification
    industry:       Optional[str] = None
    founded_year:   Optional[int] = None

    # Links
    linkedin_url:   Optional[str] = None
    twitter_url:    Optional[str] = None
    email:          Optional[str] = None
    phone:          Optional[str] = None

    # Meta
    scrape_success: bool = False
    scrape_error:   Optional[str] = None
    used_playwright: bool = False
# app/processing/cleaner.py

import re
from urllib.parse import urlparse
from app.scraping.base import ScrapedData


# ── Junk filters ──────────────────────────────────────────────────────────────

# If the "company name" matches any of these, the record is noise
JUNK_NAME_PATTERNS = [
    r'^(home|index|welcome|untitled|page not found|403|404|error)$',
    r'^https?://',   # URL leaked into name field
]

# Domains that are directories/aggregators, not actual companies
JUNK_DOMAINS = {
    "clutch.co", "g2.com", "crunchbase.com", "tracxn.com",
    "linkedin.com", "glassdoor.com", "indeed.com",
    "wikipedia.org", "facebook.com", "twitter.com", "x.com",
    "reddit.com", "youtube.com", "medium.com", "quora.com",
}

# Descriptions shorter than this are useless
MIN_DESCRIPTION_LEN = 20


# ── Normalisation helpers ─────────────────────────────────────────────────────

def normalise_url(url: str) -> str:
    """https://www.Example.com/page → example.com"""
    try:
        parsed = urlparse(url.lower().strip())
        host = parsed.netloc or parsed.path
        host = host.removeprefix("www.")
        # Strip trailing slash and path — domain is the key
        return host.split("/")[0]
    except Exception:
        return url.lower().strip()


def normalise_name(name: str) -> str:
    """'  ACME Corp.  ' → 'Acme Corp'"""
    if not name:
        return name
    name = name.strip()
    # Remove trailing punctuation like periods
    name = name.rstrip(".")
    # Title-case only if it's ALL CAPS (some sites do this)
    if name.isupper():
        name = name.title()
    return name


def normalise_description(text: str) -> str:
    if not text:
        return text
    # Collapse multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # Truncate absurdly long descriptions (probably scraped the whole page)
    if len(text) > 1000:
        text = text[:1000].rsplit(' ', 1)[0] + "…"
    return text


def normalise_employee_bounds(
    emp_min: int | None,
    emp_max: int | None
) -> tuple[int | None, int | None]:
    """Fix obviously wrong values."""
    if emp_min is not None and emp_min < 0:
        emp_min = None
    if emp_max is not None and emp_max < 0:
        emp_max = None
    # min > max is nonsensical — drop both rather than guess
    if emp_min is not None and emp_max is not None:
        if emp_min > emp_max:
            return None, None
    return emp_min, emp_max


def normalise_founded_year(year: int | None) -> int | None:
    if year is None:
        return None
    # Companies founded before 1900 or after current year are data errors
    if year < 1900 or year > 2026:
        return None
    return year


def normalise_linkedin(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    # Ensure it's a company URL, not a person profile
    if "linkedin.com/company/" not in url:
        return None
    # Ensure https
    if not url.startswith("http"):
        url = "https://" + url
    # Strip tracking params
    url = url.split("?")[0].rstrip("/")
    return url


def normalise_email(email: str | None) -> str | None:
    if not email:
        return None
    email = email.strip().lower()
    # Basic sanity check
    if "@" not in email or "." not in email.split("@")[-1]:
        return None
    return email


# ── Junk detection ────────────────────────────────────────────────────────────

def is_junk(record: ScrapedData) -> tuple[bool, str]:
    """
    Returns (is_junk, reason).
    A record is junk if we can't do anything useful with it.
    """
    domain = normalise_url(record.url)

    # Came from a directory/aggregator — not an actual company page
    if any(domain.endswith(d) for d in JUNK_DOMAINS):
        return True, f"aggregator domain: {domain}"

    # No name AND no description — nothing to classify
    if not record.name and not record.description:
        return True, "no name and no description"

    # Name looks like a browser error page
    if record.name:
        for pattern in JUNK_NAME_PATTERNS:
            if re.match(pattern, record.name.strip().lower()):
                return True, f"junk name: {record.name}"

    # Description is too short to be meaningful
    if record.description and len(record.description) < MIN_DESCRIPTION_LEN:
        if not record.name:
            return True, "description too short and no name"

    return False, ""


# ── Main cleaner ──────────────────────────────────────────────────────────────

def clean(records: list[ScrapedData]) -> list[ScrapedData]:
    """
    Normalise all fields on every record.
    Does NOT deduplicate — that's deduplicator.py's job.
    Returns a new list; original records are not mutated.
    """
    cleaned = []

    for record in records:
        junk, reason = is_junk(record)
        if junk:
            print(f"[cleaner] dropping {record.url} — {reason}")
            continue

        emp_min, emp_max = normalise_employee_bounds(
            record.employee_min, record.employee_max
        )

        cleaned.append(ScrapedData(
            url=record.url,
            source_name=record.source_name,

            name=normalise_name(record.name) if record.name else None,
            description=normalise_description(record.description) if record.description else None,
            tagline=record.tagline,

            country=record.country,
            city=record.city,
            address=record.address,

            employee_range=record.employee_range,
            employee_min=emp_min,
            employee_max=emp_max,

            industry=record.industry,
            founded_year=normalise_founded_year(record.founded_year),

            linkedin_url=normalise_linkedin(record.linkedin_url),
            twitter_url=record.twitter_url,
            email=normalise_email(record.email),
            phone=record.phone,

            scrape_success=record.scrape_success,
            scrape_error=record.scrape_error,
            used_playwright=record.used_playwright,
        ))

    print(f"[cleaner] {len(cleaned)} kept, {len(records) - len(cleaned)} dropped")
    return cleaned
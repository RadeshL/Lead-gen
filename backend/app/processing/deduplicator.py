# app/processing/deduplicator.py

from urllib.parse import urlparse
from app.scraping.base import ScrapedData


def _domain(url: str) -> str:
    """Canonical domain — the deduplication key."""
    try:
        host = urlparse(url.lower()).netloc or url.lower()
        return host.removeprefix("www.").split("/")[0]
    except Exception:
        return url.lower()


def _richness(record: ScrapedData) -> int:
    """
    Score how much useful data a record has.
    When two records share a domain, we keep the richer one.
    """
    score = 0
    if record.name:           score += 2
    if record.description:    score += 2
    if record.employee_min:   score += 3   # employee count is hard to get
    if record.country:        score += 1
    if record.city:           score += 1
    if record.linkedin_url:   score += 2
    if record.founded_year:   score += 1
    if record.email:          score += 1
    if record.industry:       score += 1
    return score


def _merge(primary: ScrapedData, secondary: ScrapedData) -> ScrapedData:
    """
    Fill gaps in `primary` with values from `secondary`.
    primary is always the richer record.
    """
    def pick(a, b):
        return a if a is not None else b

    return ScrapedData(
        url=primary.url,
        source_name=primary.source_name,

        name=pick(primary.name, secondary.name),
        description=pick(primary.description, secondary.description),
        tagline=pick(primary.tagline, secondary.tagline),

        country=pick(primary.country, secondary.country),
        city=pick(primary.city, secondary.city),
        address=pick(primary.address, secondary.address),

        employee_range=pick(primary.employee_range, secondary.employee_range),
        employee_min=pick(primary.employee_min, secondary.employee_min),
        employee_max=pick(primary.employee_max, secondary.employee_max),

        industry=pick(primary.industry, secondary.industry),
        founded_year=pick(primary.founded_year, secondary.founded_year),

        linkedin_url=pick(primary.linkedin_url, secondary.linkedin_url),
        twitter_url=pick(primary.twitter_url, secondary.twitter_url),
        email=pick(primary.email, secondary.email),
        phone=pick(primary.phone, secondary.phone),

        scrape_success=primary.scrape_success,
        scrape_error=primary.scrape_error,
        used_playwright=primary.used_playwright,
    )


def deduplicate(records: list[ScrapedData]) -> list[ScrapedData]:
    """
    Deduplicate by domain. When duplicates exist, keep the richest record
    and fill any gaps from the others.
    """
    # Group by domain
    groups: dict[str, list[ScrapedData]] = {}
    for record in records:
        key = _domain(record.url)
        groups.setdefault(key, []).append(record)

    result = []
    dupes = 0

    for domain, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
            continue

        dupes += len(group) - 1

        # Sort richest first
        ranked = sorted(group, key=_richness, reverse=True)

        # Start with the richest, fill gaps from the rest
        merged = ranked[0]
        for secondary in ranked[1:]:
            merged = _merge(merged, secondary)

        result.append(merged)

    print(f"[deduplicator] {len(records)} → {len(result)} records ({dupes} duplicates merged)")
    return result
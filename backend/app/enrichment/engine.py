# app/enrichment/engine.py

import asyncio
from urllib.parse import urlparse
from app.scraping.base import ScrapedData
from app.enrichment.base import EnrichmentResult
from app.enrichment.sources.linkedin  import enrich_from_linkedin, find_linkedin_url
from app.enrichment.sources.glassdoor import enrich_from_glassdoor, find_glassdoor_url
from app.enrichment.sources.clearbit  import enrich_from_clearbit


def _domain(url: str) -> str:
    try:
        host = urlparse(url.lower()).netloc or url
        return host.removeprefix("www.").split("/")[0]
    except Exception:
        return url


def _apply(record: ScrapedData, enrichment: EnrichmentResult) -> ScrapedData:
    """
    Fill gaps in record with enrichment values.
    Never overwrites a field that already has a value —
    the company's own website is the most authoritative source.
    """
    def fill(current, new):
        return current if current is not None else new

    record.name          = fill(record.name,          enrichment.name)
    record.description   = fill(record.description,   enrichment.description)
    record.country       = fill(record.country,       enrichment.country)
    record.city          = fill(record.city,          enrichment.city)
    record.industry      = fill(record.industry,      enrichment.industry)
    record.founded_year  = fill(record.founded_year,  enrichment.founded_year)
    record.linkedin_url  = fill(record.linkedin_url,  enrichment.linkedin_url)

    # Employee count — only fill if completely missing
    if record.employee_min is None and enrichment.employee_min is not None:
        record.employee_min   = enrichment.employee_min
        record.employee_max   = enrichment.employee_max
        record.employee_range = enrichment.employee_range

    return record


async def enrich_one(record: ScrapedData) -> ScrapedData:
    """Run all enrichment sources for a single company."""
    domain = _domain(record.url)
    name   = record.name or domain

    enrichments: list[EnrichmentResult] = []

    # ── 1. LinkedIn ──────────────────────────────────────────
    linkedin_url = record.linkedin_url

    # If we don't have a LinkedIn URL, search for one
    if not linkedin_url:
        print(f"[enrichment] searching LinkedIn for: {name}")
        linkedin_url = await find_linkedin_url(name, domain)

    if linkedin_url:
        li = await enrich_from_linkedin(linkedin_url)
        enrichments.append(li)

    # ── 2. Glassdoor ────────────────────────────────────────
    # Only fetch Glassdoor if employee count is still missing
    if record.employee_min is None:
        gd_url = await find_glassdoor_url(name)
        if gd_url:
            gd = await enrich_from_glassdoor(gd_url)
            enrichments.append(gd)

    # ── 3. Clearbit ─────────────────────────────────────────
    # Always run — it's fast, free, and fills name/domain gaps
    cb = await enrich_from_clearbit(domain)
    enrichments.append(cb)

    # Apply enrichments in order: LinkedIn > Glassdoor > Clearbit
    # (fill() never overwrites existing values so order matters less)
    for enrichment in enrichments:
        record = _apply(record, enrichment)

    return record


async def enrich_all(
    records: list[ScrapedData],
    concurrency: int = 5,
) -> list[ScrapedData]:
    """
    Enrich all records with a concurrency limit.
    Returns enriched records in the same order.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def limited(record: ScrapedData) -> ScrapedData:
        async with semaphore:
            try:
                enriched = await enrich_one(record)
                await asyncio.sleep(0.5)   # polite delay between companies
                return enriched
            except Exception as e:
                print(f"[enrichment] failed for {record.url}: {e}")
                return record              # return original on failure

    tasks = [limited(r) for r in records]
    results = await asyncio.gather(*tasks)

    filled = sum(
        1 for before, after in zip(records, results)
        if before.employee_min is None and after.employee_min is not None
    )
    print(f"[enrichment] filled employee count for {filled}/{len(records)} companies")
    return list(results)
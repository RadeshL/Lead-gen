# app/enrichment/sources/clearbit.py

import httpx
from app.enrichment.base import EnrichmentResult


async def enrich_from_clearbit(domain: str) -> EnrichmentResult:
    """
    Clearbit's free autocomplete API — no key required.
    Returns name, domain, and occasionally location.
    """
    result = EnrichmentResult(source="clearbit")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://autocomplete.clearbit.com/v1/companies/suggest",
                params={"query": domain},
            )

            if r.status_code != 200:
                return result

            companies = r.json()
            if not companies:
                return result

            # First result is usually the best match
            match = companies[0]

            result.name        = match.get("name")
            result.domain      = match.get("domain")
            result.confidence  = 0.75

    except Exception as e:
        print(f"[clearbit] failed for {domain}: {e}")

    return result
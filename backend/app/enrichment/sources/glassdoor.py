# app/enrichment/sources/glassdoor.py

import re
from typing import Optional
from duckduckgo_search import DDGS 
import httpx
from bs4 import BeautifulSoup
from app.enrichment.base import EnrichmentResult
from app.scraping.parsers import parse_employee_range

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
}


async def find_glassdoor_url(company_name: str) -> Optional[str]:
    from duckduckgo_search import DDGS
    import asyncio

    query = f"site:glassdoor.com/Overview {company_name}"
    try:
        results = await asyncio.to_thread(_ddg_search, query)
        for r in results:
            url = r.get("href", "")
            if "glassdoor.com/Overview" in url:
                return url
    except Exception:
        pass
    return None


def _ddg_search(query: str) -> list:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=5))


async def enrich_from_glassdoor(glassdoor_url: str) -> EnrichmentResult:
    result = EnrichmentResult(source="glassdoor")

    try:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=15, follow_redirects=True
        ) as client:
            r = await client.get(glassdoor_url)

            if r.status_code != 200:
                return result

            soup = BeautifulSoup(r.text, "lxml")

            # Glassdoor puts key facts in a definition list
            # <div class="infoEntity"><label>Size</label><span>51 to 200 employees</span></div>
            for row in soup.select(".infoEntity, [data-test='employer-stats'] li"):
                label = row.select_one("label, .title")
                value = row.select_one("span, .value")

                if not label or not value:
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                if "size" in label_text or "employee" in label_text:
                    mn, mx, raw = parse_employee_range(value_text)
                    if mn is not None:
                        result.employee_min   = mn
                        result.employee_max   = mx
                        result.employee_range = raw

                elif "industry" in label_text or "sector" in label_text:
                    result.industry = value_text

                elif "founded" in label_text:
                    m = re.search(r'(19|20)\d{2}', value_text)
                    if m:
                        result.founded_year = int(m.group(0))

                elif "headquarters" in label_text or "location" in label_text:
                    parts = [p.strip() for p in value_text.split(",")]
                    if len(parts) >= 2:
                        result.city    = parts[0]
                        result.country = parts[-1]

            result.confidence = 0.85

    except Exception as e:
        print(f"[glassdoor] failed for {glassdoor_url}: {e}")

    return result
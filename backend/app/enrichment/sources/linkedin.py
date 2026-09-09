# app/enrichment/sources/linkedin.py

import re
import httpx
from typing import Optional
from duckduckgo_search import DDGS 
from bs4 import BeautifulSoup
from app.enrichment.base import EnrichmentResult
from app.scraping.parsers import parse_employee_range

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


async def find_linkedin_url(company_name: str, domain: str) -> Optional[str]:
    """
    Search DuckDuckGo for the LinkedIn company page URL.
    Used when scraping didn't find a LinkedIn link on the company website.
    """
    from duckduckgo_search import DDGS
    import asyncio

    query = f"site:linkedin.com/company {company_name} {domain}"
    try:
        results = await asyncio.to_thread(_ddg_search, query)
        for r in results:
            url = r.get("href", "")
            if "linkedin.com/company/" in url:
                return url.split("?")[0].rstrip("/")
    except Exception:
        pass
    return None


def _ddg_search(query: str) -> list:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=5))


async def enrich_from_linkedin(linkedin_url: str) -> EnrichmentResult:
    result = EnrichmentResult(source="linkedin")

    try:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=15, follow_redirects=True
        ) as client:
            r = await client.get(linkedin_url)

            if r.status_code != 200:
                return result

            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text(" ", strip=True)

            # ── Company name ────────────────────────────────
            h1 = soup.find("h1")
            if h1:
                result.name = h1.get_text(strip=True)

            # ── Description ─────────────────────────────────
            about = soup.select_one(
                "[data-test-id='about-us__description'], "
                ".org-about-us-organization-description, "
                ".core-section-container__content p"
            )
            if about:
                result.description = about.get_text(strip=True)

            # ── Employee count ───────────────────────────────
            # LinkedIn renders "51-200 employees" in several places
            emp_patterns = [
                r'(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)\s*employees?',
                r'(\d+)\+?\s*employees?',
            ]
            for pat in emp_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    mn, mx, raw = parse_employee_range(m.group(0))
                    if mn is not None:
                        result.employee_min  = mn
                        result.employee_max  = mx
                        result.employee_range = raw
                        break

            # ── Industry ─────────────────────────────────────
            industry_el = soup.select_one(
                "[data-test-id='about-us__industry'] dd, "
                ".org-about-company-module__industry"
            )
            if industry_el:
                result.industry = industry_el.get_text(strip=True)

            # ── Founded year ─────────────────────────────────
            founded_el = soup.select_one(
                "[data-test-id='about-us__foundedOn'] dd, "
                ".org-about-company-module__founded"
            )
            if founded_el:
                text_val = founded_el.get_text(strip=True)
                m = re.search(r'(19|20)\d{2}', text_val)
                if m:
                    result.founded_year = int(m.group(0))

            # ── Location ─────────────────────────────────────
            hq_el = soup.select_one(
                "[data-test-id='about-us__headquarters'] dd, "
                ".org-about-company-module__headquarters"
            )
            if hq_el:
                hq = hq_el.get_text(strip=True)
                # "Bangalore, Karnataka, India" → parse city + country
                parts = [p.strip() for p in hq.split(",")]
                if len(parts) >= 2:
                    result.city    = parts[0]
                    result.country = parts[-1]
                elif parts:
                    result.city = parts[0]

            result.linkedin_url = linkedin_url
            result.confidence   = 0.90

    except Exception as e:
        print(f"[linkedin] failed for {linkedin_url}: {e}")

    return result
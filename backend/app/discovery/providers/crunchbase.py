# app/discovery/providers/crunchbase.py

import httpx
from bs4 import BeautifulSoup
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.processing.query_parser import ParsedQuery

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

class CrunchbaseProvider(DiscoveryProvider):
    name = "crunchbase"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        candidates = []
        loc      = query.city or query.country or ""
        industry = query.industry or ""

        search_url = (
            f"https://www.crunchbase.com/discover/organization.companies"
            f"?facet%5B%5D=facet_ids%3Acompany"
            f"&location_uids={loc}&category_uids={industry}"
        )

        # Crunchbase's discover page is JS-heavy — we get what we can from
        # the raw HTML (company cards often appear in meta tags)
        try:
            async with httpx.AsyncClient(timeout=20, headers=HEADERS) as client:
                r = await client.get(search_url)
                soup = BeautifulSoup(r.text, "lxml")

                for tag in soup.find_all("a", href=True):
                    href = tag["href"]
                    if "/organization/" in href:
                        full = f"https://www.crunchbase.com{href}" if href.startswith("/") else href
                        name = tag.get_text(strip=True)
                        candidates.append(CandidateCompany(
                            url=full,
                            name=name,
                            source=self.name,
                        ))
        except Exception:
            pass

        return candidates
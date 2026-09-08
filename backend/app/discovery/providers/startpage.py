# app/discovery/providers/startpage.py

import httpx
import asyncio
from bs4 import BeautifulSoup
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.discovery.query_builder import build_search_queries
from app.processing.query_parser import ParsedQuery

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class StartpageProvider(DiscoveryProvider):
    name = "startpage"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        # Only run 2 queries — Startpage blocks aggressive scraping
        queries = build_search_queries(query)[:2]
        candidates = []

        async with httpx.AsyncClient(
            timeout=20, headers=HEADERS, follow_redirects=True
        ) as client:
            for q in queries:
                try:
                    r = await client.get(
                        "https://www.startpage.com/search",
                        params={"q": q, "language": "english"},
                    )

                    soup = BeautifulSoup(r.text, "lxml")

                    # Startpage wraps results in .w-gl__result
                    for result in soup.select(".w-gl__result, [data-testid='result']"):
                        a = result.select_one("a[href^='http']")
                        title = result.select_one("h3, .w-gl__result-title")
                        desc = result.select_one("p, .w-gl__result-description")

                        if not a:
                            continue

                        candidates.append(CandidateCompany(
                            url=a["href"],
                            name=title.get_text(strip=True) if title else "",
                            description=desc.get_text(strip=True) if desc else "",
                            source=self.name,
                        ))

                    # Be polite — avoid triggering bot detection
                    await asyncio.sleep(2.0)

                except Exception as e:
                    print(f"[startpage] failed: {e}")
                    continue

        return candidates
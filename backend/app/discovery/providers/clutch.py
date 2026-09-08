# app/discovery/providers/clutch.py

import httpx
from bs4 import BeautifulSoup
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.processing.query_parser import ParsedQuery

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadBot/1.0)"}

class ClutchProvider(DiscoveryProvider):
    name = "clutch"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        candidates = []
        loc      = (query.country or "").lower().replace(" ", "-")
        industry = (query.industry or "software").lower().replace(" ", "-")
        url = f"https://clutch.co/directory/software-development/{loc}"

        try:
            async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
                r = await client.get(url)
                soup = BeautifulSoup(r.text, "lxml")

                for item in soup.select(".provider-list-item, .sg-provider"):
                    name_tag = item.select_one("h3 a, .company-name a")
                    desc_tag = item.select_one(".tagline, .summary")
                    loc_tag  = item.select_one(".locality")

                    if not name_tag:
                        continue

                    href = name_tag.get("href", "")
                    candidates.append(CandidateCompany(
                        url=f"https://clutch.co{href}" if href.startswith("/") else href,
                        name=name_tag.get_text(strip=True),
                        description=desc_tag.get_text(strip=True) if desc_tag else "",
                        city=loc_tag.get_text(strip=True) if loc_tag else None,
                        source=self.name,
                    ))
        except Exception:
            pass

        return candidates
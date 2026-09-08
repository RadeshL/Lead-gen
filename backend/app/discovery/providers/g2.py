# app/discovery/providers/g2.py

import httpx
from bs4 import BeautifulSoup
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.processing.query_parser import ParsedQuery

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadBot/1.0)"}

class G2Provider(DiscoveryProvider):
    name = "g2"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        candidates = []
        industry = (query.industry or "saas").lower().replace(" ", "-")
        url = f"https://www.g2.com/categories/{industry}"

        try:
            async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
                r = await client.get(url)
                soup = BeautifulSoup(r.text, "lxml")

                for card in soup.select("[data-product-id]"):
                    name_tag = card.select_one(".product-name, h3, h2")
                    link_tag = card.select_one("a[href*='/products/']")
                    desc_tag = card.select_one(".product-description, p")

                    name = name_tag.get_text(strip=True) if name_tag else ""
                    href = link_tag["href"] if link_tag else ""
                    desc = desc_tag.get_text(strip=True) if desc_tag else ""

                    if href:
                        full_url = f"https://www.g2.com{href}" if href.startswith("/") else href
                        candidates.append(CandidateCompany(
                            url=full_url,
                            name=name,
                            description=desc,
                            source=self.name,
                        ))
        except Exception:
            pass

        return candidates
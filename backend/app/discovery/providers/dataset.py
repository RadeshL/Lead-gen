# app/discovery/providers/dataset.py

import httpx
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.processing.query_parser import ParsedQuery

# Publicly available company datasets on GitHub
DATASETS = [
    # awesome-indian-startups style lists
    "https://raw.githubusercontent.com/geekodour/awesome-saas/master/README.md",
    # Fortune 500 / startup lists (markdown parsed for URLs)
    # Add more raw GitHub dataset URLs here as you find them
]

class DatasetProvider(DiscoveryProvider):
    name = "dataset"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        candidates = []
        country  = (query.country  or "").lower()
        industry = (query.industry or "").lower()

        async with httpx.AsyncClient(timeout=20) as client:
            for url in DATASETS:
                try:
                    r = await client.get(url)
                    candidates.extend(
                        self._parse_markdown(r.text, country, industry)
                    )
                except Exception:
                    continue

        return candidates

    def _parse_markdown(self, text: str, country: str, industry: str) -> list[CandidateCompany]:
        import re
        candidates = []
        # Find markdown links: [Name](url)
        for match in re.finditer(r'\[([^\]]+)\]\((https?://[^\)]+)\)', text):
            name, url = match.group(1), match.group(2)
            candidates.append(CandidateCompany(
                url=url,
                name=name,
                source=self.name,
            ))
        return candidates
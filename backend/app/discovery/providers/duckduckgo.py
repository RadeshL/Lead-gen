# app/discovery/providers/duckduckgo.py

import asyncio
from duckduckgo_search import DDGS
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.discovery.query_builder import build_search_queries
from app.processing.query_parser import ParsedQuery

class DuckDuckGoProvider(DiscoveryProvider):
    name = "duckduckgo"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        candidates: list[CandidateCompany] = []
        queries = build_search_queries(query)[:6]  # DDG rate-limits, keep it modest

        for q in queries:
            try:
                results = await asyncio.to_thread(self._search_sync, q)
                candidates.extend(results)
            except Exception:
                continue

        return candidates

    def _search_sync(self, query: str) -> list[CandidateCompany]:
        candidates = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=10):
                candidates.append(CandidateCompany(
                    url=r.get("href", ""),
                    name=r.get("title", ""),
                    description=r.get("body", ""),
                    source=self.name,
                ))
        return candidates
# app/discovery/engine.py

import asyncio
from urllib.parse import urlparse
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.processing.query_parser import ParsedQuery

# Import all providers
# app/discovery/engine.py

from app.discovery.providers.duckduckgo import DuckDuckGoProvider
from app.discovery.providers.google_cse  import GoogleCSEProvider        # ← new
from app.discovery.providers.startpage   import StartpageProvider    # ← new
from app.discovery.providers.crunchbase  import CrunchbaseProvider
from app.discovery.providers.g2          import G2Provider
from app.discovery.providers.clutch      import ClutchProvider
from app.discovery.providers.dataset     import DatasetProvider

class DiscoveryEngine:
    def __init__(self):
        self.providers = [
            DuckDuckGoProvider(),    
            GoogleCSEProvider(),     
            StartpageProvider(),     
            CrunchbaseProvider(),    
            G2Provider(),            
            ClutchProvider(),        
            DatasetProvider(),       
        ]

    async def discover(self, query: ParsedQuery) -> list[CandidateCompany]:
        """Run all providers in parallel, deduplicate, filter noise."""

        # Run every provider concurrently — failures return []
        tasks = [self._safe_search(p, query) for p in self.providers]
        results = await asyncio.gather(*tasks)

        # Flatten
        all_candidates: list[CandidateCompany] = []
        for batch in results:
            all_candidates.extend(batch)

        # Deduplicate by domain
        seen: set[str] = set()
        unique: list[CandidateCompany] = []
        for c in all_candidates:
            if not c.url:
                continue
            domain = c.domain()
            if domain in seen:
                continue
            seen.add(domain)
            unique.append(c)

        return unique

    async def _safe_search(
        self, provider: DiscoveryProvider, query: ParsedQuery
    ) -> list[CandidateCompany]:
        """Wrap each provider so one failure never kills the whole run."""
        try:
            return await asyncio.wait_for(provider.search(query), timeout=30)
        except Exception as e:
            print(f"[discovery] {provider.name} failed: {e}")
            return []
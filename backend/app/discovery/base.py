# app/discovery/base.py

from abc import ABC, abstractmethod
from app.processing.query_parser import ParsedQuery
from app.discovery.models import CandidateCompany

class DiscoveryProvider(ABC):
    """Every provider must implement this interface."""

    name: str = "base"

    @abstractmethod
    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        """Return candidate companies. Never raise — return [] on failure."""
        ...

    def _safe_url(self, url: str) -> str:
        if not url.startswith("http"):
            return "https://" + url
        return url
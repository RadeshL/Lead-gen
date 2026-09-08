# app/discovery/providers/google_cse.py

import httpx
import asyncio
from datetime import date
from app.discovery.base import DiscoveryProvider
from app.discovery.models import CandidateCompany
from app.discovery.query_builder import build_search_queries
from app.processing.query_parser import ParsedQuery
from app.config import settings

# Free tier: 100 queries/day across your entire project
DAILY_LIMIT = 100

# Simple in-memory counter — resets when server restarts (fine for dev)
# In production, move this to Redis with a TTL of 86400s
_usage: dict[str, int] = {}


def _today() -> str:
    return date.today().isoformat()


def _queries_used_today() -> int:
    return _usage.get(_today(), 0)


def _increment_usage(n: int = 1):
    key = _today()
    _usage[key] = _usage.get(key, 0) + n


def _queries_remaining() -> int:
    return max(0, DAILY_LIMIT - _queries_used_today())


class GoogleCSEProvider(DiscoveryProvider):
    name = "google_cse"
    BASE = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: ParsedQuery) -> list[CandidateCompany]:
        if not getattr(settings, "GOOGLE_CSE_API_KEY", None):
            return []

        remaining = _queries_remaining()
        if remaining == 0:
            print(f"[google_cse] daily limit reached ({DAILY_LIMIT}/day), skipping")
            return []

        candidates = []
        # Build all queries but only run as many as we have budget for
        all_queries = build_search_queries(query)
        queries_to_run = all_queries[:remaining]  # never exceed what's left

        if len(all_queries) > remaining:
            print(
                f"[google_cse] budget: {remaining} queries left today, "
                f"running {len(queries_to_run)} of {len(all_queries)}"
            )

        async with httpx.AsyncClient(timeout=15) as client:
            for q in queries_to_run:
                try:
                    r = await client.get(self.BASE, params={
                        "key": settings.GOOGLE_CSE_API_KEY,
                        "cx":  settings.GOOGLE_CSE_ID,
                        "q":   q,
                        "num": 10,
                    })

                    data = r.json()

                    # Quota exceeded mid-run (409 or specific error code)
                    if r.status_code == 429 or (
                        "error" in data and
                        data["error"].get("code") in (429, 403)
                    ):
                        print(f"[google_cse] quota exceeded mid-run, stopping")
                        # Mark remaining budget as 0 so future calls skip fast
                        _increment_usage(remaining)
                        break

                    _increment_usage(1)

                    for item in data.get("items", []):
                        candidates.append(CandidateCompany(
                            url=item.get("link", ""),
                            name=item.get("title", ""),
                            description=item.get("snippet", ""),
                            source=self.name,
                        ))

                    # Small delay between calls — CSE rate-limits burst requests
                    await asyncio.sleep(0.3)

                except Exception as e:
                    print(f"[google_cse] query failed: {e}")
                    continue

        print(
            f"[google_cse] done — used {_queries_used_today()}/{DAILY_LIMIT} today, "
            f"{_queries_remaining()} remaining"
        )
        return candidates


# Expose remaining count for health/status endpoints
def google_cse_status() -> dict:
    return {
        "used_today": _queries_used_today(),
        "limit": DAILY_LIMIT,
        "remaining": _queries_remaining(),
        "date": _today(),
    }
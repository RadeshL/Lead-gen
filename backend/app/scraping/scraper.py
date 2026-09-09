# app/scraping/scraper.py

import asyncio
from app.scraping.base import ScrapedData
from app.scraping.http_scraper import scrape_with_http, needs_playwright
from app.scraping.playwright_scraper import scrape_with_playwright
from app.discovery.models import CandidateCompany

# Max concurrent scrapers — be polite, avoid bans
HTTP_CONCURRENCY      = 10
PLAYWRIGHT_CONCURRENCY = 3   # Playwright is expensive


async def scrape_all(candidates: list[CandidateCompany]) -> list[ScrapedData]:
    """
    Scrape all candidates. Returns ScrapedData for every URL attempted,
    including failures (check scrape_success field).
    """
    print(f"[scraper] starting {len(candidates)} candidates")

    # Phase 1: HTTP scraping in batches
    http_semaphore = asyncio.Semaphore(HTTP_CONCURRENCY)
    http_results = await _scrape_batch_http(candidates, http_semaphore)

    # Phase 2: Playwright fallback for anything that needs it
    playwright_queue = [
        (candidates[i], http_results[i])
        for i in range(len(candidates))
        if needs_playwright(candidates[i].url, http_results[i])
    ]

    print(
        f"[scraper] HTTP done — "
        f"{sum(1 for r in http_results if r.scrape_success)} succeeded, "
        f"{len(playwright_queue)} escalating to Playwright"
    )

    if playwright_queue:
        pw_semaphore = asyncio.Semaphore(PLAYWRIGHT_CONCURRENCY)
        pw_results = await _scrape_batch_playwright(playwright_queue, pw_semaphore)

        # Merge: replace failed HTTP results with Playwright results
        pw_map = {c.url: result for c, result in zip(
            [item[0] for item in playwright_queue], pw_results
        )}
        final = [pw_map.get(r.url, r) for r in http_results]
    else:
        final = http_results

    succeeded = sum(1 for r in final if r.scrape_success)
    print(f"[scraper] done — {succeeded}/{len(final)} successful")
    return final


async def _scrape_batch_http(
    candidates: list[CandidateCompany],
    semaphore: asyncio.Semaphore,
) -> list[ScrapedData]:
    tasks = [
        _limited_http(c, semaphore) for c in candidates
    ]
    return await asyncio.gather(*tasks)


async def _limited_http(
    candidate: CandidateCompany,
    semaphore: asyncio.Semaphore,
) -> ScrapedData:
    async with semaphore:
        result = await scrape_with_http(candidate.url, name_hint=candidate.name)
        # Small delay between requests to the same domain isn't enforced here
        # but the semaphore keeps overall concurrency bounded
        await asyncio.sleep(0.1)
        return result


async def _scrape_batch_playwright(
    queue: list[tuple[CandidateCompany, ScrapedData]],
    semaphore: asyncio.Semaphore,
) -> list[ScrapedData]:
    tasks = [
        _limited_playwright(candidate, semaphore)
        for candidate, _ in queue
    ]
    return await asyncio.gather(*tasks)


async def _limited_playwright(
    candidate: CandidateCompany,
    semaphore: asyncio.Semaphore,
) -> ScrapedData:
    async with semaphore:
        result = await scrape_with_playwright(candidate.url, name_hint=candidate.name)
        await asyncio.sleep(0.5)
        return result
# app/scraping/http_scraper.py

import httpx
from app.scraping.base import ScrapedData
from app.scraping.parsers import parse_page

HEADERS = { 
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

# Sites that are definitely JS-rendered — go straight to Playwright
PLAYWRIGHT_DOMAINS = {
    "angel.co", "wellfound.com", "crunchbase.com",
    "tracxn.com", "glassdoor.com",
}


async def scrape_with_http(url: str, name_hint: str = None) -> ScrapedData:
    result = ScrapedData(url=url, source_name=name_hint)

    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
            http2=True,
        ) as client:
            r = await client.get(url)

            # JS-gated: body is too small or has no meaningful text
            if r.status_code == 403:
                result.scrape_error = "403 forbidden"
                return result

            if r.status_code != 200:
                result.scrape_error = f"HTTP {r.status_code}"
                return result

            html = r.text

            # If page is suspiciously small it's probably a JS shell
            if len(html) < 2000:
                result.scrape_error = "page_too_small"
                return result

            extracted = parse_page(html, url, name_hint=name_hint)
            for key, value in extracted.items():
                if value is not None:
                    setattr(result, key, value)

            result.scrape_success = True

    except httpx.TimeoutException:
        result.scrape_error = "timeout"
    except httpx.RequestError as e:
        result.scrape_error = f"request_error: {e}"
    except Exception as e:
        result.scrape_error = f"unknown: {e}"

    return result


def needs_playwright(url: str, result: ScrapedData) -> bool:
    """Decide whether to escalate to Playwright."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.removeprefix("www.")

    if domain in PLAYWRIGHT_DOMAINS:
        return True

    if result.scrape_error in ("page_too_small", "403 forbidden"):
        return True

    # If we got a page but couldn't extract even a name, try Playwright
    if result.scrape_success and not result.name and not result.description:
        return True

    return False
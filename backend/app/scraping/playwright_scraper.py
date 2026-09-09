# app/scraping/playwright_scraper.py

from playwright.async_api import async_playwright
from app.scraping.base import ScrapedData
from app.scraping.parsers import parse_page


async def scrape_with_playwright(url: str, name_hint: str = None) -> ScrapedData:
    result = ScrapedData(url=url, source_name=name_hint, used_playwright=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )

            page = await context.new_page()

            # Block images, fonts, media — we only need HTML
            await page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "media", "font", "stylesheet")
                else route.continue_(),
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=20000)

            # Wait a moment for any lazy-loaded content
            await page.wait_for_timeout(1500)

            html = await page.content()
            await browser.close()

            extracted = parse_page(html, url, name_hint=name_hint)
            for key, value in extracted.items():
                if value is not None:
                    setattr(result, key, value)

            result.scrape_success = bool(result.name or result.description)
            if not result.scrape_success:
                result.scrape_error = "no_content_extracted"

    except Exception as e:
        result.scrape_error = f"playwright: {e}"

    return result
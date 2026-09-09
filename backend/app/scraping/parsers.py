# app/scraping/parsers.py

import re
from typing import Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.scraping.base import ScrapedData


# ── Employee range patterns ───────────────────────────────────────────────────

EMPLOYEE_PATTERNS = [
    # "11-50 employees", "51–200 employees"
    (r'(\d+)\s*[-–]\s*(\d+)\s*employees?', lambda m: (int(m.group(1)), int(m.group(2)))),
    # "50+ employees"
    (r'(\d+)\+\s*employees?',              lambda m: (int(m.group(1)), None)),
    # "fewer than 10 employees"
    (r'fewer than\s*(\d+)\s*employees?',   lambda m: (1, int(m.group(1)))),
    # "over 500 employees"
    (r'over\s*(\d+)\s*employees?',         lambda m: (int(m.group(1)), None)),
    # LinkedIn style ranges in meta: "1,001-5,000"
    (r'(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)',    lambda m: (
        int(m.group(1).replace(",", "")),
        int(m.group(2).replace(",", ""))
    )),
]

EMPLOYEE_RANGE_LABELS = {
    "self-employed": (1, 1),
    "1-10": (1, 10), "2-10": (2, 10),
    "11-50": (11, 50),
    "51-200": (51, 200),
    "201-500": (201, 500),
    "501-1000": (501, 1000),
    "1001-5000": (1001, 5000),
    "5001-10000": (5001, 10000),
    "10001+": (10001, None),
}


def parse_employee_range(text: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Returns (min, max, raw_string). All three can be None on failure."""
    if not text:
        return None, None, None

    clean = text.strip()

    # Check known label map first
    for label, (mn, mx) in EMPLOYEE_RANGE_LABELS.items():
        if label in clean.lower():
            return mn, mx, clean

    # Try regex patterns
    for pattern, extractor in EMPLOYEE_PATTERNS:
        m = re.search(pattern, clean, re.IGNORECASE)
        if m:
            try:
                mn, mx = extractor(m)
                return mn, mx, clean
            except Exception:
                continue

    return None, None, None


# ── Company name ─────────────────────────────────────────────────────────────

def extract_name(soup: BeautifulSoup, url: str, hint: Optional[str] = None) -> Optional[str]:
    """Try multiple signals, return best guess."""

    # 1. og:site_name is usually the cleanest company name
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    # 2. <title> — strip common suffixes
    title = soup.find("title")
    if title:
        raw = title.get_text(strip=True)
        # Remove " | Tagline", " - Home", " | About Us" etc.
        clean = re.split(r'\s*[|\-–—]\s*', raw)[0].strip()
        if clean and len(clean) < 80:
            return clean

    # 3. og:title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content", "").strip():
        raw = og_title["content"].strip()
        return re.split(r'\s*[|\-–—]\s*', raw)[0].strip()

    # 4. h1 — often the brand name on landing pages
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        if text and len(text) < 80:
            return text

    # 5. Fall back to discovery hint (name from search result)
    if hint:
        return hint.split("|")[0].split("-")[0].strip()

    # 6. Domain as last resort
    domain = urlparse(url).netloc.removeprefix("www.").split(".")[0]
    return domain.capitalize() if domain else None


# ── Description ──────────────────────────────────────────────────────────────

def extract_description(soup: BeautifulSoup) -> Optional[str]:
    # 1. og:description — usually the best written summary
    og = soup.find("meta", property="og:description")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    # 2. meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content", "").strip():
        return meta["content"].strip()

    # 3. Twitter description
    tw = soup.find("meta", attrs={"name": "twitter:description"})
    if tw and tw.get("content", "").strip():
        return tw["content"].strip()

    # 4. First substantial paragraph in <main> or <article>
    for container in soup.select("main, article, section, .about, #about"):
        for p in container.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 80:
                return text

    return None


# ── Location ─────────────────────────────────────────────────────────────────

COUNTRY_SIGNALS = {
    "india": "India", "indian": "India",
    "usa": "USA", "united states": "USA", "u.s.": "USA",
    "uk": "UK", "united kingdom": "UK",
    "singapore": "Singapore",
    "canada": "Canada",
    "australia": "Australia",
    "germany": "Germany",
}

CITY_SIGNALS = [
    "Bangalore", "Bengaluru", "Mumbai", "Delhi", "New Delhi",
    "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad",
    "San Francisco", "New York", "Austin", "Seattle", "Boston",
    "London", "Berlin", "Singapore", "Toronto", "Sydney",
]


def extract_location(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Returns (country, city)."""

    # 1. JSON-LD structured data — most reliable when present
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            addr = data.get("address", {})
            if addr:
                country = addr.get("addressCountry") or addr.get("country")
                city    = addr.get("addressLocality") or addr.get("city")
                return _normalise_country(country), city
        except Exception:
            continue

    # 2. Look for location-flavoured text across the page
    text = soup.get_text(" ", strip=True).lower()

    country = None
    for signal, name in COUNTRY_SIGNALS.items():
        if signal in text:
            country = name
            break

    city = None
    for c in CITY_SIGNALS:
        if c.lower() in text:
            city = c
            break

    return country, city


def _normalise_country(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    mapping = {"IN": "India", "US": "USA", "GB": "UK", "SG": "Singapore"}
    return mapping.get(raw.upper(), raw)


# ── Founded year ──────────────────────────────────────────────────────────────

def extract_founded_year(soup: BeautifulSoup) -> Optional[int]:
    text = soup.get_text(" ", strip=True)

    # "Founded in 2015", "Est. 2012", "Since 2018", "Founded: 2019"
    patterns = [
        r'founded\s*(?:in)?\s*:?\s*(20\d{2}|19\d{2})',
        r'est\.?\s*(20\d{2}|19\d{2})',
        r'since\s+(20\d{2}|19\d{2})',
        r'established\s+(?:in\s+)?(20\d{2}|19\d{2})',
        r'incorporated\s+(?:in\s+)?(20\d{2}|19\d{2})',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            year = int(m.group(1))
            if 1900 <= year <= 2026:
                return year

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            founded = data.get("foundingDate", "")
            if founded:
                m = re.search(r'(20\d{2}|19\d{2})', str(founded))
                if m:
                    return int(m.group(1))
        except Exception:
            continue

    return None


# ── Social / contact links ────────────────────────────────────────────────────

def extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, Optional[str]]:
    result = {
        "linkedin_url": None,
        "twitter_url":  None,
        "email":        None,
        "phone":        None,
    }

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if not result["linkedin_url"] and "linkedin.com/company" in href:
            result["linkedin_url"] = href if href.startswith("http") else urljoin(base_url, href)

        if not result["twitter_url"] and (
            "twitter.com/" in href or "x.com/" in href
        ) and "/intent/" not in href:
            result["twitter_url"] = href if href.startswith("http") else urljoin(base_url, href)

        if not result["email"] and href.startswith("mailto:"):
            result["email"] = href.replace("mailto:", "").split("?")[0].strip()

        if not result["phone"] and href.startswith("tel:"):
            result["phone"] = href.replace("tel:", "").strip()

    return result


# ── Employee count from visible text ─────────────────────────────────────────

def extract_employee_info(soup: BeautifulSoup) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Scan full page text for employee count signals."""

    # Priority: structured data first
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            emp = data.get("numberOfEmployees")
            if emp:
                val = emp.get("value") if isinstance(emp, dict) else emp
                mn, mx, raw = parse_employee_range(str(val))
                if mn is not None:
                    return mn, mx, raw
        except Exception:
            continue

    # Scan meta tags
    for meta in soup.find_all("meta"):
        content = meta.get("content", "")
        if "employee" in content.lower() or re.search(r'\d+\s*[-–]\s*\d+', content):
            mn, mx, raw = parse_employee_range(content)
            if mn is not None:
                return mn, mx, raw

    # Scan visible text — look near "employee" keyword
    text = soup.get_text(" ", strip=True)
    # Find sentences containing employee signals
    for sentence in re.split(r'[.|\n]', text):
        if "employee" in sentence.lower() or "team size" in sentence.lower() or "team of" in sentence.lower():
            mn, mx, raw = parse_employee_range(sentence)
            if mn is not None:
                return mn, mx, raw

    return None, None, None


# ── Master extractor ──────────────────────────────────────────────────────────

def parse_page(html: str, url: str, name_hint: Optional[str] = None) -> dict:
    """Run all extractors against a page. Returns a dict ready to merge into ScrapedData."""
    soup = BeautifulSoup(html, "lxml")

    country, city = extract_location(soup)
    emp_min, emp_max, emp_range = extract_employee_info(soup)
    social = extract_social_links(soup, url)

    return {
        "name":           extract_name(soup, url, hint=name_hint),
        "description":    extract_description(soup),
        "country":        country,
        "city":           city,
        "employee_min":   emp_min,
        "employee_max":   emp_max,
        "employee_range": emp_range,
        "founded_year":   extract_founded_year(soup),
        **social,
    }
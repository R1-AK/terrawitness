"""
Fetches a news article URL and returns clean plain text + metadata.
Handles Mongabay Indonesia, Betahita, Tempo Lingkungan, Kompas.
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Tags and classes to strip (nav, ads, footers, etc.)
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form",
              "noscript", "iframe", "figure", "figcaption"]

NOISE_CLASSES = ["related", "sidebar", "widget", "comment", "share", "social",
                 "advertisement", "promo", "newsletter", "popup"]


def _clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for cls in NOISE_CLASSES:
        for el in soup.find_all(class_=re.compile(cls, re.I)):
            el.decompose()
    return soup


def _extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    if soup.title:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def _extract_date(soup: BeautifulSoup) -> str:
    # Try <time> tag first
    time_tag = soup.find("time")
    if time_tag:
        return time_tag.get("datetime", time_tag.get_text(strip=True))

    # Try meta tags
    for prop in ["article:published_time", "og:published_time", "datePublished"]:
        meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if meta and meta.get("content"):
            return meta["content"][:10]

    return ""


def _extract_body(soup: BeautifulSoup) -> str:
    # Try common article containers
    for selector in [
        {"class_": re.compile(r"article[_-]?(body|content|text)", re.I)},
        {"class_": re.compile(r"entry[_-]?(content|text)", re.I)},
        {"class_": re.compile(r"post[_-]?(content|body)", re.I)},
        {"itemprop": "articleBody"},
    ]:
        container = soup.find(["div", "article", "section"], **selector)
        if container:
            return container.get_text(separator="\n", strip=True)

    # Fallback: all <p> tags
    paragraphs = soup.find_all("p")
    return "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 60)


def fetch_article(url: str) -> dict:
    """
    Fetch a news article and return:
    {
        "url": str,
        "title": str,
        "date": str,
        "text": str,       # clean article body
        "source": str,     # domain name
        "word_count": int,
    }
    Returns None if fetch fails.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
    except requests.RequestException as e:
        print(f"  [parser] Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    soup = _clean_soup(soup)

    title = _extract_title(soup)
    date = _extract_date(soup)
    body = _extract_body(soup)

    # Derive source domain
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "")

    # Truncate to ~6000 chars to stay within Claude context limits
    body_truncated = body[:6000]

    return {
        "url": url,
        "title": title,
        "date": date,
        "text": body_truncated,
        "source": domain,
        "word_count": len(body.split()),
    }

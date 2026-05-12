"""
RSS feed monitor: fetches articles matching mining/ecological violation keywords
from Indonesian environmental news sources.
"""

import feedparser

RSS_FEEDS = [
    # Investigative / environmental specialist
    "https://mongabay.co.id/feed/",
    "https://www.betahita.id/feed/",
    "https://forestdigest.com/feed/",
    # National newspapers
    "https://rss.kompas.com/",
    "https://rss.kompas.com/nasional",
    "https://www.kompas.com/tag/nikel.rss",
    # Tempo
    "https://www.tempo.co/rss/nasional",
    "https://www.tempo.co/rss/bisnis",
    "https://www.tempo.co/rss/lingkungan",
    # Antara (state news agency — most reliable RSS)
    "https://www.antaranews.com/rss/topnews.xml",
    "https://www.antaranews.com/rss/ekonomi.xml",
    "https://www.antaranews.com/rss/lingkungan.xml",
    # CNN Indonesia
    "https://www.cnnindonesia.com/rss",
    "https://www.cnnindonesia.com/ekonomi/rss",
    # Detik
    "https://rss.detik.com/index.php/detikcom",
    "https://finance.detik.com/rss",
    # Kumparan
    "https://kumparan.com/topic/nikel/rss",
]

# Bahasa Indonesia keywords for ecological violations in mining regions
VIOLATION_KEYWORDS = [
    # Mining activity
    "tambang", "pertambangan", "nikel", "batubara", "bauksit", "tembaga",
    "IUP", "IUPK", "smelter", "RKAB",
    # Environmental harm
    "pencemaran", "limbah", "tailing", "sedimentasi", "kerusakan lingkungan",
    "illegal", "ilegal", "melanggar",
    # Ecosystem types
    "hutan lindung", "kawasan hutan", "mangrove", "taman nasional",
    "sungai", "DAS", "pesisir",
    # Community impact
    "warga", "masyarakat", "nelayan", "petani", "air bersih",
    # National / policy terms more common in Kompas/Tempo/Antara
    "AMDAL", "izin lingkungan", "moratorium", "reklamasi", "ekspor nikel",
    "bijih nikel", "ESDM", "KLHK", "smelter", "hilirisasi",
    "Morowali", "Halmahera", "Wawonii", "Kabaena", "Raja Ampat",
    "Konawe", "Bombana", "Kolaka",
]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def get_articles_from_feed(feed_url: str, max_articles: int = 20) -> list[dict]:
    """
    Fetch a single RSS feed and return matching article metadata.
    Returns list of {url, title, summary, published} dicts.
    """
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"  [rss] Failed to parse {feed_url}: {e}")
        return []

    matches = []
    for entry in feed.entries[:max_articles]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        combined = f"{title} {summary}"

        if _matches_keywords(combined, VIOLATION_KEYWORDS):
            matches.append({
                "url": entry.get("link", ""),
                "title": title,
                "summary": summary,
                "published": entry.get("published", ""),
                "feed_source": feed_url,
            })

    return matches


def get_all_articles(max_per_feed: int = 10) -> list[dict]:
    """Fetch matching articles from all configured RSS feeds."""
    all_articles = []
    for feed_url in RSS_FEEDS:
        print(f"  [rss] Checking {feed_url} ...")
        articles = get_articles_from_feed(feed_url, max_per_feed)
        print(f"        → {len(articles)} matching articles")
        all_articles.extend(articles)
    return all_articles

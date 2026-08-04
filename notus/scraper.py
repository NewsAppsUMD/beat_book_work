#!/usr/bin/env python3
"""
NOTUS House and Senate Scraper

Scrapes House and Senate section articles from notus.org via the site's
monthly sitemaps, which reach much further back in time than the RSS feed,
and merges them into the same date-based JSON files used by rss_parser.py.
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

SITEMAP_INDEX_URL = "https://www.notus.org/sitemap.xml"
SECTIONS = ("house", "senate")
SECTION_PATTERN = re.compile(
    r"^https://www\.notus\.org/(?:" + "|".join(SECTIONS) + r")/[^/]+$"
)

OUTPUT_DIR = Path(__file__).parent / "data"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})

# notus.org's robots.txt specifies a 10 second crawl delay.
DEFAULT_DELAY = 10


def fetch_monthly_sitemaps() -> list[str]:
    """Fetch monthly sitemap URLs (sitemap-YYYYMM.xml) from the sitemap index, oldest first."""
    response = SESSION.get(SITEMAP_INDEX_URL, timeout=30)
    response.raise_for_status()
    locs = re.findall(r"<loc>([^<]+)</loc>", response.text)
    monthly = [loc for loc in locs if re.search(r"sitemap-\d{6}\.xml$", loc)]
    return sorted(monthly)


def fetch_section_urls(sitemap_url: str) -> list[str]:
    """Fetch House/Senate article URLs listed in one monthly sitemap."""
    try:
        response = SESSION.get(sitemap_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {sitemap_url}: {e}")
        return []

    locs = re.findall(r"<loc>([^<]+)</loc>", response.text)
    return [loc for loc in locs if SECTION_PATTERN.match(loc)]


def parse_article_json_ld(soup: BeautifulSoup) -> dict | None:
    """Extract the schema.org Article block from an article page's JSON-LD."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (TypeError, json.JSONDecodeError):
            continue
        if data.get("@type") == "Article":
            return data
    return None


def fetch_article(url: str) -> dict | None:
    """Fetch an article page and build a JSON entry matching the notus schema."""
    try:
        response = SESSION.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    article_data = parse_article_json_ld(soup)
    if not article_data:
        print(f"No article data found for {url}")
        return None

    body = soup.find("div", class_="article__body")
    paragraphs = body.find_all("p") if body else []
    content = "\n\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())

    published = datetime.fromisoformat(article_data["datePublished"].replace("Z", "+00:00"))
    authors = [a.get("name", "") for a in article_data.get("author", []) if a.get("name")]
    section = urlparse(url).path.strip("/").split("/")[0]

    return {
        "title": article_data.get("headline") or article_data.get("name", ""),
        "link": url,
        "published": published.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "published_parsed": published.isoformat(),
        "summary": article_data.get("description", ""),
        "content": content,
        "author": ", ".join(authors),
        "id": url,
        "tags": [section],
    }


def save_entries_to_json(entries: list[dict]) -> int:
    """Save entries to one JSON file per day, merging with any existing entries."""
    entries_by_date = {}
    for entry in entries:
        entry_date = datetime.fromisoformat(entry["published_parsed"])
        date_key = entry_date.strftime("%Y-%m-%d")
        entries_by_date.setdefault(date_key, []).append(entry)

    total_added = 0
    for date_key, new_entries in entries_by_date.items():
        entry_date = datetime.strptime(date_key, "%Y-%m-%d")
        date_dir = OUTPUT_DIR / str(entry_date.year) / date_key
        date_dir.mkdir(parents=True, exist_ok=True)
        filepath = date_dir / f"{date_key}.json"

        existing_entries = []
        existing_ids = set()
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                existing_entries = existing_data.get("entries", [])
                existing_ids = {e.get("id") or e.get("link") for e in existing_entries}
            except json.JSONDecodeError:
                print(f"Warning: Could not parse existing file {filepath}, will overwrite")

        added_count = 0
        for entry in new_entries:
            entry_id = entry.get("id") or entry.get("link")
            if entry_id not in existing_ids:
                existing_entries.append(entry)
                existing_ids.add(entry_id)
                added_count += 1

        daily_data = {
            "date": date_key,
            "entry_count": len(existing_entries),
            "entries": existing_entries,
            "last_updated": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(daily_data, f, indent=2, ensure_ascii=False)

        total_added += added_count
        if added_count:
            print(f"Added {added_count} new entries to {filepath} (total: {len(existing_entries)})")

    return total_added


def scrape_sections(months: list[str] | None = None, delay: float = DEFAULT_DELAY) -> int:
    """Scrape House and Senate articles from the given (or all) monthly sitemaps."""
    sitemap_urls = fetch_monthly_sitemaps()
    if months:
        sitemap_urls = [u for u in sitemap_urls if any(m in u for m in months)]

    seen_urls = set()
    total_saved = 0
    for sitemap_url in sitemap_urls:
        print(f"Scanning {sitemap_url}...")
        time.sleep(delay)
        article_urls = fetch_section_urls(sitemap_url)
        print(f"  Found {len(article_urls)} House/Senate articles")

        entries = []
        for i, url in enumerate(article_urls):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            print(f"  Processing {i + 1}/{len(article_urls)}: {url}")
            time.sleep(delay)
            entry = fetch_article(url)
            if entry:
                entries.append(entry)

        total_saved += save_entries_to_json(entries)

    return total_saved


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape NOTUS House and Senate stories from the site's sitemaps"
    )
    parser.add_argument(
        "--months",
        nargs="+",
        help="Limit to specific YYYYMM sitemap months (default: all available months, back to 2023)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Seconds to wait between requests (default: {DEFAULT_DELAY}, per notus.org's robots.txt)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    global OUTPUT_DIR
    if args.output:
        OUTPUT_DIR = args.output

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total = scrape_sections(months=args.months, delay=args.delay)
    print(f"\nTotal: Saved {total} new articles to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

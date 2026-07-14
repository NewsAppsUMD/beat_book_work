#!/usr/bin/env python3
"""
Maryland Matters Daily Scraper

Scrapes only the latest story from each category and outputs JSON files.
Designed to run daily via GitHub Actions.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import feedparser
import requests


CATEGORIES = {
    "politics": "https://marylandmatters.org/category/politics/feed/",
    "environment": "https://marylandmatters.org/category/environment/feed/",
    "health": "https://marylandmatters.org/category/health/feed/",
    "education": "https://marylandmatters.org/category/education/feed/",
    "justice": "https://marylandmatters.org/category/justice/feed/",
    "transportation": "https://marylandmatters.org/category/transportation/feed/",
    "work-economy": "https://marylandmatters.org/category/work-economy/feed/",
}

OUTPUT_DIR = Path(__file__).parent / "data"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})


def fetch_latest_article(feed_url: str) -> dict | None:
    """Fetch only the latest article from RSS feed."""
    try:
        response = SESSION.get(feed_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching feed {feed_url}: {e}")
        return None

    feed = feedparser.parse(response.content)

    if not feed.entries:
        return None

    # Get the first (most recent) entry
    entry = feed.entries[0]

    return {
        "title": entry.get("title", ""),
        "link": entry.get("link", ""),
        "published": entry.get("published", ""),
        "published_parsed": format_published_date(entry.get("published_parsed")),
        "summary": entry.get("summary", ""),
        "author": get_author(entry),
        "id": entry.get("link", ""),
        "categories": [cat.term for cat in entry.get("tags", [])],
    }


def get_author(entry: feedparser.FeedParserDict) -> str:
    """Extract author from entry, checking multiple fields."""
    if hasattr(entry, "author"):
        return entry.author
    if hasattr(entry, "dc_creator"):
        return entry.dc_creator
    if hasattr(entry, "contributors"):
        contributors = entry.contributors
        if contributors:
            return contributors[0].get("name", "")
    return ""


def format_published_date(parsed_date) -> str:
    """Format parsed date to ISO format."""
    if parsed_date:
        return datetime(*parsed_date[:6]).isoformat()
    return ""


def fetch_full_content(article_url: str) -> str:
    """Fetch full article content using BeautifulSoup to extract articleContainer."""
    try:
        response = SESSION.get(article_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the article content in articleContainer div
        article_container = soup.find('div', class_='articleContainer')
        if article_container:
            paragraphs = article_container.find_all('p')
            text = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            return text

        return ""
    except Exception as e:
        print(f"Error fetching {article_url}: {e}")
        return ""


def create_entry_json(article_data: dict, content_text: str) -> dict:
    """Create JSON entry matching notus schema."""
    return {
        "title": article_data["title"],
        "link": article_data["link"],
        "published": article_data["published"],
        "published_parsed": article_data["published_parsed"],
        "summary": article_data["summary"],
        "content": content_text,
        "author": article_data["author"],
        "id": article_data["id"],
        "tags": article_data.get("categories", []),
    }


def scrape_category(category_slug: str, feed_url: str) -> bool:
    """Scrape latest story from a single category and save JSON file."""
    print(f"Scraping {category_slug}...")

    category_dir = OUTPUT_DIR / category_slug
    category_dir.mkdir(parents=True, exist_ok=True)

    article_data = fetch_latest_article(feed_url)

    if not article_data:
        print(f"  No articles found in feed")
        return False

    print(f"  Latest: {article_data['title'][:50]}...")

    # Fetch full content
    content_text = fetch_full_content(article_data["link"])

    if not content_text:
        # Fallback: use summary as content
        content_text = article_data.get("summary", "")
        print(f"  Using summary as content (full content unavailable)")
    else:
        print(f"  Fetched full content ({len(content_text)} chars)")

    # Create entry JSON
    entry = create_entry_json(article_data, content_text)

    # Generate filename from URL
    url_path = urlparse(article_data["link"]).path
    slug = url_path.strip("/").split("/")[-1]
    filename = f"{slug}.json"

    # Save JSON file
    output_path = category_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)

    print(f"  Saved to {output_path}")
    return True


def main():
    """Main entry point."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_saved = 0
    for category_slug, feed_url in CATEGORIES.items():
        try:
            if scrape_category(category_slug, feed_url):
                total_saved += 1
        except Exception as e:
            print(f"Error scraping {category_slug}: {e}")

    print(f"\nTotal: Saved {total_saved}/7 categories")

    if total_saved == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

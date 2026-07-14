#!/usr/bin/env python3
"""
Maryland Matters Scraper

Scrapes stories from Maryland Matters category pages using RSS feeds,
extracts full content with newspaper4k, and outputs JSON files.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from dateutil import parser as date_parser
from newspaper import Article


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


def fetch_article_urls_from_feed(feed_url: str, pages: int = 5) -> list[dict]:
    """Fetch article metadata from RSS feed with pagination support."""
    articles = []

    # WordPress RSS feeds support ?paged=N parameter
    for page in range(1, pages + 1):
        url = feed_url.rstrip("/")
        if page > 1:
            url = f"{url}?paged={page}"

        try:
            response = SESSION.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching feed page {page}: {e}")
            break

        feed = feedparser.parse(response.content)

        if not feed.entries:
            break

        for entry in feed.entries:
            article_data = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "published_parsed": format_published_date(entry.get("published_parsed")),
                "summary": entry.get("summary", ""),
                "author": get_author(entry),
                "id": entry.get("link", ""),
                "categories": [cat.term for cat in entry.get("tags", [])],
            }
            articles.append(article_data)

    return articles


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


def fetch_full_content(article_url: str) -> tuple[str, str]:
    """Fetch full article content using newspaper4k."""
    try:
        article = Article(article_url)
        article.download()
        article.parse()
        return article.text, article.html
    except Exception as e:
        print(f"Error fetching {article_url}: {e}")
        return "", ""


def create_entry_json(article_data: dict, content_html: str) -> dict:
    """Create JSON entry matching notus schema."""
    return {
        "title": article_data["title"],
        "link": article_data["link"],
        "published": article_data["published"],
        "published_parsed": article_data["published_parsed"],
        "summary": article_data["summary"],
        "content": content_html,
        "author": article_data["author"],
        "id": article_data["id"],
        "tags": article_data.get("categories", []),
    }


def scrape_category(category_slug: str, feed_url: str, max_pages: int = 5) -> int:
    """Scrape a single category and save JSON files."""
    print(f"Scraping {category_slug}...")

    category_dir = OUTPUT_DIR / category_slug
    category_dir.mkdir(parents=True, exist_ok=True)

    articles = fetch_article_urls_from_feed(feed_url, pages=max_pages)
    print(f"  Found {len(articles)} articles in feed")

    saved_count = 0
    for i, article_data in enumerate(articles):
        print(f"  Processing {i + 1}/{len(articles)}: {article_data['title'][:50]}...")

        # Fetch full content
        content_text, content_html = fetch_full_content(article_data["link"])

        if not content_html:
            # Fallback: use summary as content if newspaper fails
            content_html = article_data.get("summary", "")

        # Create entry JSON
        entry = create_entry_json(article_data, content_html)

        # Generate filename from URL
        url_path = urlparse(article_data["link"]).path
        slug = url_path.strip("/").split("/")[-1]
        filename = f"{slug}.json"

        # Save JSON file
        output_path = category_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)

        saved_count += 1

    print(f"  Saved {saved_count} articles to {category_dir}")
    return saved_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Scrape Maryland Matters stories")
    parser.add_argument("--pages", type=int, default=5, help="Max pages per category")
    parser.add_argument("--category", type=str, help="Scrape single category only")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    global OUTPUT_DIR
    if args.output:
        OUTPUT_DIR = args.output

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    categories_to_scrape = CATEGORIES
    if args.category:
        if args.category not in CATEGORIES:
            print(f"Unknown category: {args.category}")
            print(f"Available: {', '.join(CATEGORIES.keys())}")
            sys.exit(1)
        categories_to_scrape = {args.category: CATEGORIES[args.category]}

    total_saved = 0
    for category_slug, feed_url in categories_to_scrape.items():
        try:
            count = scrape_category(category_slug, feed_url, max_pages=args.pages)
            total_saved += count
        except Exception as e:
            print(f"Error scraping {category_slug}: {e}")

    print(f"\nTotal: Saved {total_saved} articles to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

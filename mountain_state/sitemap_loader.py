#!/usr/bin/env python3
"""
Sitemap Loader for Mountain State Spotlight
Fetches all story URLs from XML sitemaps, downloads full text via newspaper4k,
and writes entries to day-specific JSON files matching the RSS parser format.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

import requests
from newspaper import Article


SITEMAP_URLS = [
    "https://mountainstatespotlight.org/post-sitemap.xml",
    "https://mountainstatespotlight.org/post-sitemap2.xml",
]

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch_sitemap_urls(sitemap_url):
    """Fetch and parse a sitemap XML, returning a list of (url, lastmod) tuples."""
    print(f"Fetching sitemap: {sitemap_url}")
    resp = requests.get(sitemap_url, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    entries = []
    for url_elem in root.findall("sm:url", SITEMAP_NS):
        loc = url_elem.findtext("sm:loc", namespaces=SITEMAP_NS)
        lastmod = url_elem.findtext("sm:lastmod", namespaces=SITEMAP_NS)
        if loc:
            entries.append((loc, lastmod))

    print(f"  Found {len(entries)} URLs")
    return entries


def download_article(url):
    """Download and parse a single article using newspaper4k."""
    article = Article(url)
    article.download()
    article.parse()
    return article


def article_to_entry(article, url, lastmod):
    """Convert a newspaper Article to an entry dict matching the RSS parser format."""
    pub_date = article.publish_date
    if pub_date is None and lastmod:
        pub_date = datetime.fromisoformat(lastmod.replace("Z", "+00:00"))

    published_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S %z") if pub_date else ""
    published_parsed = pub_date.isoformat() if pub_date else None

    authors = article.authors
    author_str = ", ".join(authors) if authors else ""

    return {
        "title": article.title or "",
        "link": url,
        "published": published_str,
        "published_parsed": published_parsed,
        "summary": article.meta_description or "",
        "content": article.text or "",
        "author": author_str,
        "id": url,
        "tags": list(article.meta_keywords) if article.meta_keywords else [],
    }


def get_date_key(entry):
    """Extract a YYYY-MM-DD date key from an entry."""
    if entry["published_parsed"]:
        dt = datetime.fromisoformat(entry["published_parsed"])
        return dt.strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")


def save_entries_to_json(entries, base_dir="data"):
    """Save entries to day-specific JSON files, matching the RSS parser structure."""
    base_path = Path(base_dir)

    entries_by_date = {}
    for entry in entries:
        date_key = get_date_key(entry)
        entries_by_date.setdefault(date_key, []).append(entry)

    for date_key, new_entries in entries_by_date.items():
        entry_date = datetime.strptime(date_key, "%Y-%m-%d")
        date_dir = base_path / str(entry_date.year) / date_key
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
                pass

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

        if added_count > 0:
            print(f"  Added {added_count} entries to {filepath} (total: {len(existing_entries)})")


def main():
    all_urls = []
    for sitemap_url in SITEMAP_URLS:
        all_urls.extend(fetch_sitemap_urls(sitemap_url))

    print(f"\nTotal URLs to process: {len(all_urls)}")

    entries = []
    for i, (url, lastmod) in enumerate(all_urls, 1):
        print(f"[{i}/{len(all_urls)}] {url}")
        try:
            article = download_article(url)
            entry = article_to_entry(article, url, lastmod)
            entries.append(entry)
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nSuccessfully processed {len(entries)} articles")
    save_entries_to_json(entries)
    print("Done.")


if __name__ == "__main__":
    main()

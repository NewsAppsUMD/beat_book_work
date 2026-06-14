#!/usr/bin/env python3
"""
RSS Feed Parser for Mountain State Spotlight
Parses RSS feed and saves entries to JSON files organized by year and date.
"""

import feedparser
import json
from pathlib import Path
from datetime import datetime


def parse_feed(feed_url):
    """Parse RSS feed and return entries."""
    print(f"Fetching feed from {feed_url}...")
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        print(f"Warning: Feed parsing had issues: {feed.bozo_exception}")

    print(f"Feed title: {feed.feed.get('title', 'Unknown')}")
    print(f"Found {len(feed.entries)} entries")

    return feed


def get_entry_date(entry):
    """Extract and parse the published date from an entry."""
    date_tuple = entry.get('published_parsed') or entry.get('updated_parsed')

    if date_tuple:
        return datetime(*date_tuple[:6])

    return datetime.now()


def save_entries_to_json(feed, base_dir='data'):
    """Save feed entries to a single JSON file per day, organized by year and date."""
    base_path = Path(base_dir)

    # Group entries by date
    entries_by_date = {}
    for entry in feed.entries:
        entry_date = get_entry_date(entry)
        date_key = entry_date.strftime('%Y-%m-%d')

        if date_key not in entries_by_date:
            entries_by_date[date_key] = []

        content_list = entry.get('content', [])
        full_text = content_list[0].get('value', '') if content_list else ''

        entry_data = {
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'published': entry.get('published', ''),
            'published_parsed': entry_date.isoformat() if entry_date else None,
            'summary': entry.get('summary', ''),
            'content': full_text,
            'author': entry.get('author', ''),
            'id': entry.get('id', ''),
            'tags': [tag.get('term', '') for tag in entry.get('tags', [])],
        }

        entries_by_date[date_key].append(entry_data)

    # Save one file per date
    for date_key, new_entries in entries_by_date.items():
        entry_date = datetime.strptime(date_key, '%Y-%m-%d')

        # Create directory structure: data/yyyy/yyyy-mm-dd/
        year_dir = base_path / str(entry_date.year)
        date_dir = year_dir / date_key
        date_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{date_key}.json"
        filepath = date_dir / filename

        # Load existing entries if file exists
        existing_entries = []
        existing_ids = set()
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_entries = existing_data.get('entries', [])
                    existing_ids = {e.get('id') or e.get('link')
                                    for e in existing_entries}
                print(f"Found {len(existing_entries)} existing entries in {filepath}")
            except json.JSONDecodeError:
                print(f"Warning: Could not parse existing file {filepath}, will overwrite")

        # Merge new entries, avoiding duplicates
        added_count = 0
        for entry in new_entries:
            entry_id = entry.get('id') or entry.get('link')
            if entry_id not in existing_ids:
                existing_entries.append(entry)
                existing_ids.add(entry_id)
                added_count += 1

        daily_data = {
            'date': date_key,
            'entry_count': len(existing_entries),
            'entries': existing_entries,
            'last_updated': datetime.now().isoformat()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(daily_data, f, indent=2, ensure_ascii=False)

        if added_count > 0:
            print(f"Added {added_count} new entries to {filepath} (total: {len(existing_entries)})")
        else:
            print(f"No new entries to add to {filepath} (total: {len(existing_entries)})")

    print(f"\nAll entries saved to {base_path}")


def main():
    """Main function to run the RSS parser."""
    feed_url = "https://mountainstatespotlight.org/feed/"

    feed = parse_feed(feed_url)
    save_entries_to_json(feed)


if __name__ == "__main__":
    main()

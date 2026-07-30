#!/usr/bin/env python3
"""
RSS Feed Parser for the Star Tribune.

Fetches the Star Tribune RSS feed(s) backing the index page at
www2.startribune.com/rss-index/112994779/ and saves each story as a JSON
object, grouped into one file per month named mm_yyyy.json (e.g. 07_2026.json).

The index page itself is JavaScript-rendered, so its feed links are not present
in the static HTML. The actual RSS endpoint for category 112994779 is
https://www2.startribune.com/rss/?c=112994779. Additional feeds can be added to
FEED_URLS below.
"""

import json
from datetime import datetime
from pathlib import Path

import feedparser

# The RSS feed(s) to retrieve. These are the feeds linked from the index page
# www2.startribune.com/rss-index/112994779/. The politics feed is currently
# broken (returns a 404 JSON body instead of RSS); it is commented out so we
# don't repeatedly hit a dead endpoint. Re-enable it once it is fixed.
FEED_URLS = [
    "https://www.startribune.com/local/index.rss2",
    "https://www.startribune.com/sports/index.rss2",
    "https://www.startribune.com/business/index.rss2",
    "https://www.startribune.com/opinion/index.rss2",
    # "https://www.startribune.com/politics/index.rss2",  # currently broken
    "https://www.startribune.com/variety/index.rss2",
    "https://www.startribune.com/video/index.rss2",
    "https://www.startribune.com/galleries/index.rss2",
]

# Browser-like user agent — some servers reject the default feedparser agent.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Where monthly JSON files are written, relative to this script.
DATA_DIR = Path(__file__).parent / "data"


def parse_feed(feed_url):
    """Fetch and parse a single RSS feed, returning the feedparser result.

    A broken or unreachable feed returns an empty feed (zero entries) rather
    than raising, so one bad feed never aborts the whole run.
    """
    print(f"Fetching feed from {feed_url}...")
    try:
        feed = feedparser.parse(feed_url, agent=USER_AGENT)
    except Exception as exc:  # network errors, etc.
        print(f"  Warning: could not fetch feed: {exc}")
        return feedparser.FeedParserDict(entries=[])

    if feed.bozo:
        print(f"  Warning: feed parsing had issues: {feed.bozo_exception}")

    print(f"  Feed title: {feed.feed.get('title', 'Unknown')}")
    print(f"  Found {len(feed.entries)} entries")
    return feed


def get_entry_date(entry):
    """Parse the published (or updated) date of an entry into a datetime."""
    date_tuple = entry.get("published_parsed") or entry.get("updated_parsed")
    if date_tuple:
        return datetime(*date_tuple[:6])
    # Fall back to "now" if no parseable date is present.
    return datetime.now()


def section_from_url(feed_url):
    """Derive a short section label (e.g. 'local') from a feed URL."""
    # Matches the path segment before /index.rss2, e.g. .../local/index.rss2
    parts = feed_url.rstrip("/").split("/")
    if "index.rss2" in parts:
        idx = parts.index("index.rss2")
        if idx > 0:
            return parts[idx - 1]
    return feed_url


def entry_to_dict(entry, source_feed=""):
    """Convert a feedparser entry into the JSON object stored for a story."""
    entry_date = get_entry_date(entry)
    return {
        "title": entry.get("title", ""),
        "link": entry.get("link", ""),
        "published": entry.get("published", ""),
        "published_parsed": entry_date.isoformat() if entry_date else None,
        "summary": entry.get("summary", ""),
        "author": entry.get("author", ""),
        "id": entry.get("id", ""),
        "content_id": entry.get("st_contentid", ""),
        "credit_line": entry.get("st_creditline", ""),
        "source": source_feed,
        "section": section_from_url(source_feed),
        "tags": [tag.get("term", "") for tag in entry.get("tags", [])],
    }


def dedup_key(story):
    """Stable identifier for a story, used to avoid duplicates across runs."""
    return story.get("content_id") or story.get("id") or story.get("link")


def save_stories_by_month(stories, base_dir=DATA_DIR):
    """Group stories by month and merge each month into its mm_yyyy.json file."""
    base_dir.mkdir(parents=True, exist_ok=True)

    # Group stories into month buckets keyed mm_yyyy, using the ISO timestamp
    # we stored on each story dict.
    by_month = {}
    for story in stories:
        entry_date = None
        try:
            entry_date = datetime.fromisoformat(story["published_parsed"])
        except (TypeError, ValueError):
            entry_date = datetime.now()
        month_key = entry_date.strftime("%m_%Y")
        by_month.setdefault(month_key, []).append(story)

    total_added = 0
    for month_key, new_stories in sorted(by_month.items()):
        filepath = base_dir / f"{month_key}.json"

        # Load any existing entries so re-runs accumulate without duplicating.
        existing_entries = []
        existing_ids = set()
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_entries = existing_data.get("entries", [])
                    existing_ids = {dedup_key(e) for e in existing_entries}
                print(f"  Found {len(existing_entries)} existing entries in {filepath.name}")
            except json.JSONDecodeError:
                print(f"  Warning: could not parse {filepath.name}, will overwrite")

        # Merge new stories, skipping ones we have already seen.
        added = 0
        for story in new_stories:
            key = dedup_key(story)
            if key in existing_ids:
                continue
            existing_entries.append(story)
            existing_ids.add(key)
            added += 1
        total_added += added

        monthly_data = {
            "month": month_key,
            "entry_count": len(existing_entries),
            "entries": existing_entries,
            "last_updated": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(monthly_data, f, indent=2, ensure_ascii=False)

        if added > 0:
            print(f"  Added {added} new stories to {filepath.name} (total: {len(existing_entries)})")
        else:
            print(f"  No new stories for {filepath.name} (total: {len(existing_entries)})")

    print(f"\nDone. Added {total_added} new stories across {len(by_month)} month file(s) in {base_dir}")


def main():
    all_stories = []
    for feed_url in FEED_URLS:
        feed = parse_feed(feed_url)
        for entry in feed.entries:
            all_stories.append(entry_to_dict(entry, source_feed=feed_url))

    print(f"\nCollected {len(all_stories)} stories from {len(FEED_URLS)} feed(s).")
    save_stories_by_month(all_stories)


if __name__ == "__main__":
    main()
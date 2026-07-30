# Maryland Matters Scraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Python scraper that fetches stories from Maryland Matters category pages using RSS feeds, extracts full article content with newspaper-4k, and outputs JSON files matching the existing notus data schema.

**Architecture:** The scraper will use WordPress category RSS feeds (which bypass Cloudflare protection) to discover articles, then fetch each article's full text using newspaper-4k for content extraction. Each category gets its own folder with individual JSON files per story.

**Tech Stack:** Python 3.12+, uv for dependency management, newspaper-4k for text extraction, feedparser for RSS parsing, requests for HTTP.

---

### Task 1: Create Directory Structure and Initialize Project

**Files:**
- Create: `maryland_matters/`
- Create: `maryland_matters/data/`
- Create: `maryland_matters/pyproject.toml`

**Step 1: Create directory structure**

```bash
mkdir -p maryland_matters/data
```

**Step 2: Initialize uv project with dependencies**

```bash
cd maryland_matters
uv init --no-readme
uv add newspaper-4k feedparser requests python-dateutil
```

Expected: `pyproject.toml` with dependencies listed

**Step 3: Update pyproject.toml with script entry**

Modify the `[project.scripts]` section to add:
```toml
[project.scripts]
scrape = "scraper:main"
```

**Step 4: Commit**

```bash
git add maryland_matters/
git commit -m "feat: initialize maryland_matters scraper project with dependencies"
```

---

### Task 2: Create the Main Scraper Script

**Files:**
- Create: `maryland_matters/scraper.py`

**Step 1: Write the scraper module**

```python
#!/usr/bin/env python3
"""
Maryland Matters Scraper

Scrapes stories from Maryland Matters category pages using RSS feeds,
extracts full content with newspaper-4k, and outputs JSON files.
"""

import json
import os
import re
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
    """Fetch full article content using newspaper-4k."""
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    total_saved = 0
    for category_slug, feed_url in CATEGORIES.items():
        try:
            count = scrape_category(category_slug, feed_url)
            total_saved += count
        except Exception as e:
            print(f"Error scraping {category_slug}: {e}")
    
    print(f"\nTotal: Saved {total_saved} articles to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
```

**Step 2: Run the scraper to test**

```bash
cd maryland_matters
uv run python scraper.py
```

Expected: Output showing articles being scraped from each category

**Step 3: Verify output structure**

```bash
ls -la data/*/
head -50 data/politics/*.json | head -30
```

Expected: JSON files matching the notus schema with title, link, published, summary, content, author, id, tags fields

**Step 4: Commit**

```bash
git add scraper.py
git commit -m "feat: add Maryland Matters scraper with RSS feed parsing and newspaper-4k extraction"
```

---

### Task 3: Add Pagination Support and Configuration

**Files:**
- Modify: `maryland_matters/scraper.py`
- Create: `maryland_matters/config.py` (optional if config grows)

**Step 1: Add command-line arguments for pagination control**

Modify the `main()` function to accept arguments:

```python
import argparse

def main():
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
```

**Step 2: Test with command-line args**

```bash
uv run python scraper.py --category politics --pages 2
```

Expected: Only politics category scraped, 2 pages max

**Step 3: Commit**

```bash
git add scraper.py
git commit -m "feat: add CLI args for pages, category filter, and output dir"
```

---

### Task 4: Create Aggregated Daily JSON Output (Optional)

**Files:**
- Create: `maryland_matters/aggregate.py`

**Step 1: Write aggregation script**

```python
#!/usr/bin/env python3
"""Aggregate scraped stories into daily JSON files matching notus format."""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "aggregated"


def aggregate_by_date():
    """Group all stories by published date."""
    stories_by_date = defaultdict(list)
    
    for category_dir in DATA_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for json_file in category_dir.glob("*.json"):
            with open(json_file) as f:
                story = json.load(f)
            
            # Parse published date
            published = story.get("published_parsed", "")
            if published:
                date_str = published.split("T")[0]
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
            
            stories_by_date[date_str].append(story)
    
    # Write daily files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for date_str, stories in stories_by_date.items():
        output = {
            "date": date_str,
            "entry_count": len(stories),
            "entries": stories,
        }
        
        output_file = OUTPUT_DIR / f"{date_str}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"Wrote {len(stories)} stories to {output_file}")


if __name__ == "__main__":
    aggregate_by_date()
```

**Step 2: Run aggregation**

```bash
uv run python aggregate.py
```

**Step 3: Commit**

```bash
git add aggregate.py
git commit -m "feat: add aggregation script for daily JSON output"
```

---

### Task 5: Add README and Final Verification

**Files:**
- Create: `maryland_matters/README.md`

**Step 1: Write README**

```markdown
# Maryland Matters Scraper

Scrapes stories from Maryland Matters by category using RSS feeds.

## Usage

```bash
# Scrape all categories (5 pages each)
uv run python scraper.py

# Scrape specific category
uv run python scraper.py --category politics

# Scrape with custom page limit
uv run python scraper.py --pages 10

# Aggregate into daily JSON files
uv run python aggregate.py
```

## Categories

- politics
- environment
- health
- education
- justice
- transportation
- work-economy

## Output

Stories are saved to `data/<category>/<slug>.json` with schema matching notus:
- title
- link
- published
- published_parsed
- summary
- content (HTML)
- author
- id
- tags
```

**Step 2: Final verification run**

```bash
uv run python scraper.py --pages 3
ls -la data/*/
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage instructions"
```

---

## Verification Checklist

Before marking complete, verify:
- [ ] All 7 categories scrape successfully
- [ ] Pagination works (test with `--pages 2`)
- [ ] JSON output matches notus schema
- [ ] newspaper-4k extracts content correctly
- [ ] Individual JSON files per story in category folders
- [ ] `uv run` works without errors

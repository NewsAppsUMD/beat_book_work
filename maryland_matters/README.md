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

# Scrape single category with more pages
uv run python scraper.py --category politics --pages 10
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

## Dependencies

- newspaper4k - Article extraction
- feedparser - RSS feed parsing
- requests - HTTP client
- python-dateutil - Date parsing

# Star Tribune

Tool for collecting Star Tribune RSS feed content and saving each story as a JSON
object, grouped into one file per month.

## `rss_parser.py`

Fetches the Star Tribune section RSS feeds linked from the index page at
`www2.startribune.com/rss-index/112994779/` and saves each story to a JSON file
named `mm_yyyy.json` (e.g. `07_2026.json`) under `data/`.

The index page is JavaScript-rendered, so its feed links are not in the static
HTML. The feeds it links to are the section feeds in `FEED_URLS` (local, sports,
business, opinion, variety, video, galleries). The politics feed is currently
broken (returns a 404 JSON body) and is commented out. Add or re-enable feed
URLs in that list to collect additional sections.

```bash
uv run python rss_parser.py
```

Each monthly file accumulates stories over time — re-running the script merges
new stories without duplicating existing ones (deduped by `content_id` / `id` /
`link`).

**Dependencies:** `feedparser` (managed with `uv`)

### Story object fields

| Field | Description |
|-------|-------------|
| `title` | Story headline |
| `link` | Story URL |
| `published` | Raw publication date string |
| `published_parsed` | ISO 8601 publication timestamp |
| `summary` | Story description / summary |
| `author` | Byline (`dc:creator`) |
| `id` | Feed GUID |
| `content_id` | Star Tribune content ID (`st:contentID`) — only on some feeds |
| `credit_line` | Credit line (`st:creditLine`) — only on some feeds |
| `source` | Feed URL the story came from |
| `section` | Section label derived from the feed URL (e.g. `local`, `sports`) |
| `tags` | Feed category tags |

> Note: the section `.rss2` feeds carry a simpler schema than the main
> `?c=` feed — `author`, `content_id`, and `credit_line` are empty on those,
> while `title`, `link`, `id`, `summary`, `published`, and `tags` are populated.
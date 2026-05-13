import json
import glob
import os
import re
import html
import argparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np


def strip_html(text):
    """Remove HTML tags and unescape entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_entries(data_dir):
    """Load all entries from daily JSON files."""
    pattern = os.path.join(data_dir, "data", "2026", "*", "*.json")
    entries = []
    seen_ids = set()
    for filepath in sorted(glob.glob(pattern)):
        with open(filepath) as f:
            data = json.load(f)
        for entry in data.get("entries", []):
            entry_id = entry.get("id") or entry.get("link")
            if entry_id not in seen_ids:
                seen_ids.add(entry_id)
                entries.append(entry)
    return entries


def main():
    parser = argparse.ArgumentParser(description="Find niche topics via TF-IDF + K-Means clustering")
    parser.add_argument("--clusters", type=int, default=30, help="Number of clusters (default: 30)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    entries = load_entries(script_dir)
    print(f"Loaded {len(entries)} unique entries")

    # Build document texts: title + stripped summary
    docs = []
    for entry in entries:
        title = entry.get("title", "")
        summary = strip_html(entry.get("summary", ""))
        docs.append(f"{title} {summary}")

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(stop_words="english", max_df=0.5, min_df=2)
    tfidf_matrix = vectorizer.fit_transform(docs)
    feature_names = vectorizer.get_feature_names_out()
    print(f"Vocabulary size: {len(feature_names)}")

    # K-Means clustering
    k = args.clusters
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(tfidf_matrix)

    # Build clusters
    clusters = []
    for cluster_id in range(k):
        indices = [i for i, label in enumerate(labels) if label == cluster_id]
        # Top terms from cluster centroid
        centroid = km.cluster_centers_[cluster_id]
        top_indices = centroid.argsort()[-8:][::-1]
        top_terms = [feature_names[i] for i in top_indices]
        # Stories in this cluster, sorted reverse-chron
        stories = sorted(
            [
                {
                    "title": entries[i].get("title", ""),
                    "link": entries[i].get("link", ""),
                    "published_parsed": entries[i].get("published_parsed", ""),
                    "author": entries[i].get("author", ""),
                }
                for i in indices
            ],
            key=lambda s: s["published_parsed"],
            reverse=True,
        )
        clusters.append({
            "cluster_id": cluster_id,
            "top_terms": top_terms,
            "story_count": len(stories),
            "stories": stories,
        })

    # Sort clusters smallest-first (niche topics at top)
    clusters.sort(key=lambda c: c["story_count"])

    # Terminal report
    print(f"\n{'='*70}")
    print(f"TOPIC CLUSTERS (smallest first — niche topics at top)")
    print(f"{'='*70}\n")
    for c in clusters:
        terms = ", ".join(c["top_terms"])
        print(f"[{c['story_count']:3d} stories] {terms}")
        for story in c["stories"][:3]:
            print(f"             • {story['title'][:80]}")
        if c["story_count"] > 3:
            print(f"             ... and {c['story_count'] - 3} more")
        print()

    # Write JSON
    output_path = os.path.join(script_dir, "topic_clusters.json")
    with open(output_path, "w") as f:
        json.dump(clusters, f, indent=2)
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()

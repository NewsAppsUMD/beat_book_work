#!/usr/bin/env python3
"""
CLI utility for LDA topic modeling over JSON story files.

Supports three input formats:
  - RSS-parser daily files: {entries: [{title, summary, content, ...}]}
  - WordPress API exports: [{title: {rendered}, content: {rendered}, ...}]

Accepts a single JSON file or a directory (searched recursively for *.json).
"""

import json
import glob
import os
import re
import html
import argparse

from topica import LDA, tokenize
import numpy as np


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "my", "no", "not", "of", "on", "or", "our", "out",
    "said", "she", "so", "some", "than", "that", "the", "their", "them",
    "then", "there", "these", "they", "this", "to", "up", "us", "was", "we",
    "were", "what", "when", "which", "who", "will", "with", "would", "you",
    "your", "been", "being", "do", "does", "did", "doing", "about", "after",
    "all", "also", "am", "because", "before", "between", "both", "can",
    "could", "each", "few", "get", "got", "here", "him", "just",
    "know", "like", "make", "many", "may", "me", "more", "most", "much",
    "must", "new", "now", "off", "old", "one", "only", "other", "over",
    "own", "part", "per", "put", "same", "should", "show", "still", "such",
    "take", "tell", "through", "too", "under", "very", "want", "way", "well",
    "while", "why", "work", "year", "years", "it's", "don't", "i'm", "he's",
    "she's", "that's", "what's", "who's", "let's", "here's", "there's",
    "where's", "how's", "isn't", "aren't", "wasn't", "weren't", "won't",
    "wouldn't", "couldn't", "shouldn't", "hasn't", "haven't", "hadn't",
    "going", "really", "think", "even", "first", "last", "back", "right",
    "things", "thing", "something", "anything", "everything", "those",
    "where", "come", "came", "went", "go", "say", "says", "see", "seen",
    "look", "looking", "looks", "keep", "keeps", "kept", "let", "made",
    "making", "need", "needs", "set", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "since", "around", "down",
    "every", "another", "any", "given", "give", "long", "time", "times",
    "people", "called", "call", "use", "used", "using", "left",
}


def strip_html(text):
    text = html.unescape(text or "")
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b[0-9a-f]{4,}\b", " ", text)
    text = re.sub(r"\b\d+x\d+\b", " ", text)
    text = re.sub(r"\b\d{3,}\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_entry(raw):
    """Normalize a story from any supported format into a common dict."""
    # WordPress API format: title and content are {rendered: "..."}
    if isinstance(raw.get("title"), dict):
        return {
            "title": strip_html(raw["title"].get("rendered", "")),
            "link": raw.get("link", ""),
            "published_parsed": raw.get("date", ""),
            "author": "",
            "summary": strip_html(raw.get("excerpt", {}).get("rendered", "")),
            "content": strip_html(raw.get("content", {}).get("rendered", "")),
        }
    # RSS-parser format: title and content are plain strings
    return {
        "title": raw.get("title", ""),
        "link": raw.get("link", ""),
        "published_parsed": raw.get("published_parsed", ""),
        "author": raw.get("author", ""),
        "summary": strip_html(raw.get("summary", "")),
        "content": strip_html(raw.get("content", "")),
    }


def load_json_file(filepath):
    """Load stories from a single JSON file, handling both formats."""
    with open(filepath) as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "entries" in data:
        return data["entries"]
    return []


def load_stories(path):
    """Load and deduplicate stories from a file or directory."""
    if os.path.isfile(path):
        files = [path]
    else:
        files = sorted(glob.glob(os.path.join(path, "**", "*.json"), recursive=True))

    seen = set()
    stories = []
    for filepath in files:
        for raw in load_json_file(filepath):
            entry_id = raw.get("id") or raw.get("link", "")
            if entry_id and entry_id in seen:
                continue
            seen.add(entry_id)
            stories.append(normalize_entry(raw))

    return stories


def main():
    parser = argparse.ArgumentParser(
        description="LDA topic modeling over JSON story files"
    )
    parser.add_argument("input", help="Path to a JSON file or directory of JSON files")
    parser.add_argument("--topics", type=int, required=True, help="Number of topics")
    parser.add_argument("--output", required=True, help="Path for the output JSON file")
    parser.add_argument("--iters", type=int, default=1000, help="Gibbs sampling iterations (default: 1000)")
    parser.add_argument("--words", type=int, default=10, help="Top words per topic (default: 10)")
    args = parser.parse_args()

    stories = load_stories(args.input)
    print(f"Loaded {len(stories)} unique stories")

    texts = []
    for s in stories:
        title = s["title"]
        summary = s["summary"]
        content = s["content"][:2000] if s["content"] else ""
        texts.append(f"{title} {summary} {content}")

    tokenized = [[w for w in tokenize(text) if w not in STOPWORDS] for text in texts]

    docs = []
    valid_indices = []
    for i, tokens in enumerate(tokenized):
        if tokens:
            docs.append(tokens)
            valid_indices.append(i)
    print(f"Tokenized {len(docs)} documents")

    model = LDA(num_topics=args.topics, seed=42)
    model.fit(docs, iters=args.iters)

    top_words = model.top_words(args.words)
    labels = np.argmax(model.doc_topic, axis=1)

    clusters = []
    for topic_id in range(args.topics):
        indices = [i for i, label in enumerate(labels) if label == topic_id]
        top_terms = [word for word, _ in top_words[topic_id]]
        topic_stories = sorted(
            [stories[valid_indices[i]] for i in indices],
            key=lambda s: s.get("published_parsed", ""),
            reverse=True,
        )
        clusters.append({
            "topic_id": topic_id,
            "top_terms": top_terms,
            "story_count": len(topic_stories),
            "stories": topic_stories,
        })

    clusters.sort(key=lambda c: c["story_count"])

    print(f"\n{'='*70}")
    print("TOPIC CLUSTERS (smallest first)")
    print(f"{'='*70}\n")
    for c in clusters:
        terms = ", ".join(c["top_terms"])
        print(f"[Topic {c['topic_id']:2d}: {c['story_count']:3d} stories] {terms}")
        for story in c["stories"][:3]:
            print(f"             • {story['title'][:80]}")
        if c["story_count"] > 3:
            print(f"             ... and {c['story_count'] - 3} more")
        print()

    with open(args.output, "w") as f:
        json.dump(clusters, f, indent=2)
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()

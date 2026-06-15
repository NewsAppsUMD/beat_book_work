#!/usr/bin/env python3
"""
CLI utility to export all stories from a specific topic cluster.
"""

import json
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Export stories from a topic cluster to a JSON file"
    )
    parser.add_argument("input", help="Path to a topics JSON file")
    parser.add_argument("topic_id", type=int, help="Topic ID to export")
    parser.add_argument("--output", required=True, help="Path for the output JSON file")
    args = parser.parse_args()

    with open(args.input) as f:
        clusters = json.load(f)

    match = None
    for cluster in clusters:
        if cluster["topic_id"] == args.topic_id:
            match = cluster
            break

    if match is None:
        valid_ids = sorted(c["topic_id"] for c in clusters)
        print(f"Topic {args.topic_id} not found. Valid IDs: {valid_ids}")
        return

    stories = match["stories"]
    terms = ", ".join(match["top_terms"])
    print(f"Topic {args.topic_id}: {terms}")
    print(f"Exported {len(stories)} stories to {args.output}")

    with open(args.output, "w") as f:
        json.dump(stories, f, indent=2)


if __name__ == "__main__":
    main()

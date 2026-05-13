import json
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Export stories from a specific topic cluster to a JSON file")
    parser.add_argument("cluster_id", type=int, help="Cluster ID to export (use find_niche_topics.py output to identify)")
    parser.add_argument("--input", default=None, help="Path to topic_clusters.json (default: same directory as script)")
    parser.add_argument("--output", default=None, help="Output filename (default: cluster_<id>.json)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = args.input or os.path.join(script_dir, "topic_clusters.json")

    with open(input_path) as f:
        clusters = json.load(f)

    match = None
    for cluster in clusters:
        if cluster["cluster_id"] == args.cluster_id:
            match = cluster
            break

    if match is None:
        valid_ids = sorted(c["cluster_id"] for c in clusters)
        print(f"Cluster {args.cluster_id} not found. Valid IDs: {valid_ids}")
        return

    output_name = args.output or f"cluster_{args.cluster_id}.json"
    output_path = os.path.join(script_dir, output_name)

    with open(output_path, "w") as f:
        json.dump(match["stories"], f, indent=2)

    terms = ", ".join(match["top_terms"])
    print(f"Cluster {args.cluster_id}: {terms}")
    print(f"Exported {match['story_count']} stories to {output_path}")


if __name__ == "__main__":
    main()

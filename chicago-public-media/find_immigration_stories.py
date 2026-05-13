import json
import glob
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
json_files = glob.glob(os.path.join(script_dir, "data", "2026", "*", "*.json"))

matches = []

for filepath in json_files:
    with open(filepath) as f:
        data = json.load(f)
    for entry in data.get("entries", []):
        title = entry.get("title", "").lower()
        summary = entry.get("summary", "").lower()
        if "immigration" in title or "immigration" in summary:
            matches.append(entry)

matches.sort(key=lambda e: e.get("published_parsed", ""), reverse=True)

seen = set()
unique = []
for entry in matches:
    key = entry.get("id") or entry.get("link")
    if key not in seen:
        seen.add(key)
        unique.append(entry)

output_path = os.path.join(script_dir, "immigration.json")
with open(output_path, "w") as f:
    json.dump(unique, f, indent=2)

print(f"Found {len(unique)} immigration stories, written to {output_path}")

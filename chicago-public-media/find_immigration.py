import json
import glob
import os

matches = []

for json_file in sorted(glob.glob('data/**/*.json', recursive=True)):
    with open(json_file, 'r') as f:
        day_data = json.load(f)
    for entry in day_data.get('entries', []):
        summary = entry.get('summary', '')
        if 'immigration' in summary.lower():
            matches.append(entry)

output_file = 'immigration.json'
with open(output_file, 'w') as f:
    json.dump(matches, f, indent=4)

print(f"Found {len(matches)} stories mentioning immigration. Saved to {output_file}.")

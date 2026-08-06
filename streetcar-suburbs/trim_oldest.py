import json

input_file = 'streetcarsuburbs_slim.json'

with open(input_file, 'r') as f:
    posts = json.load(f)

posts.sort(key=lambda p: p['date'])
trimmed = posts[200:]

with open(input_file, 'w') as f:
    json.dump(trimmed, f, indent=4)

print(f"Removed 200 oldest posts. {len(trimmed)} posts remaining.")

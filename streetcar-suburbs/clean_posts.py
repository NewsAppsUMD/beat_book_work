import json

REMOVE_FIELDS = {'excerpt', 'ping_status', 'featured_media', 'sticky', 'template', 'comment_status', 'categories', 'tags', 'format', 'coauthors', 'author', 'modified_gmt', 'meta', 'class_list', 'newspack_spnsrs_tax', 'brand',
    'yoast_head', 'yoast_head_json', 'schema', 'parsely', '_links'}

input_file = 'streetcarsuburbs.json'
output_file = 'streetcarsuburbs.json'

with open(input_file, 'r') as f:
    posts = json.load(f)

for post in posts:
    keys_to_remove = [k for k in post if k in REMOVE_FIELDS or k.startswith('jetpack')]
    for k in keys_to_remove:
        del post[k]

with open(output_file, 'w') as f:
    json.dump(posts, f, indent=4)

print(f"Done. Cleaned {len(posts)} posts.")

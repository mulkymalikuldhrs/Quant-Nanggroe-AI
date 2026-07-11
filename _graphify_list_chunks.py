import json
from pathlib import Path
from collections import defaultdict

d = json.load(open("graphify-out/.graphify_detect.json", encoding="utf-16"))
all_files = [f for cat in ("document", "paper", "image") for f in d["files"].get(cat, [])]
scan_root = Path(d["scan_root"])

# Group by first dir
grouped = defaultdict(list)
for f in all_files:
    p = Path(f)
    try:
        rel = p.relative_to(scan_root)
        first = rel.parts[0]
    except ValueError:
        first = "(root)"
    grouped[first].append(f)

chunks = []
cur = []
for dirname in sorted(grouped.keys()):
    for f in sorted(grouped[dirname]):
        cur.append(f)
        if len(cur) >= 22:
            chunks.append(cur)
            cur = []
if cur:
    chunks.append(cur)

for i, chunk in enumerate(chunks):
    print("Chunk {:02d}: {} files ({})".format(i, len(chunk), Path(chunk[0]).relative_to(scan_root)))
    for f in chunk:
        rel = Path(f).relative_to(scan_root)
        print("  {}".format(rel))
    print()

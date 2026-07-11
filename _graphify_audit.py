import json
from collections import Counter
from pathlib import Path

d = json.load(open("graphify-out/.graphify_detect.json", encoding="utf-16"))
scan_root = Path(d["scan_root"])
all_files = []
for cat in ("code", "document", "paper", "image", "video"):
    for f in d.get("files", {}).get(cat, []):
        p = Path(f)
        if str(p).startswith(str(scan_root / "graphify-out")):
            continue
        all_files.append(p)

counter = Counter()
for p in all_files:
    try:
        rel = p.relative_to(scan_root)
        counter[rel.parts[0]] += 1
    except (ValueError, IndexError):
        counter["(root)"] += 1

print("Total files: {:d}".format(len(all_files)))
print("Total words: {:,}".format(d.get("total_words", 0)))
print()
print("Top-level directories by file count:")
for name, count in counter.most_common(10):
    print("  {}/: {} files".format(name, count))

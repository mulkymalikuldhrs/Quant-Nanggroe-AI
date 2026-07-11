import json, math, os
from pathlib import Path

detect = json.loads(Path("graphify-out/.graphify_detect.json").read_text(encoding="utf-16"))
all_files = [f for cat in ("document", "paper", "image") for f in detect["files"].get(cat, [])]

from collections import defaultdict
grouped = defaultdict(list)
for f in all_files:
    p = Path(f).relative_to(detect["scan_root"]) if Path(f).is_absolute() else Path(f)
    first_dir = p.parts[0] if len(p.parts) > 1 else "(root)"
    grouped[first_dir].append(f)

chunks = []
current_chunk = []
for dirname in sorted(grouped.keys()):
    files = sorted(grouped[dirname])
    for f in files:
        current_chunk.append(f)
        if len(current_chunk) >= 22:
            chunks.append(current_chunk)
            current_chunk = []
if current_chunk:
    chunks.append(current_chunk)

# Write chunk files
for i, chunk in enumerate(chunks):
    chunk_id = "{:02d}".format(i)
    with open("graphify-out/.graphify_chunk_{}.txt".format(chunk_id), "w", encoding="utf-8") as f:
        f.write("\n".join(chunk))

print("chunks={}".format(len(chunks)))

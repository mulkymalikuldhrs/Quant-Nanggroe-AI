import json, math
from pathlib import Path

detect = json.loads(Path("graphify-out/.graphify_detect.json").read_text(encoding="utf-16"))
all_files = [f for cat in ("document", "paper", "image") for f in detect["files"].get(cat, [])]

# Group files by their first directory component so related files land together
from collections import defaultdict
grouped = defaultdict(list)
for f in all_files:
    p = Path(f).relative_to(detect["scan_root"]) if Path(f).is_absolute() else Path(f)
    first_dir = p.parts[0] if len(p.parts) > 1 else "(root)"
    grouped[first_dir].append(f)

# Flatten groups into chunks of ~22 files
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

print("Total files: {}".format(len(all_files)))
print("Total chunks: {}".format(len(chunks)))
for i, chunk in enumerate(chunks):
    print("  chunk {:02d}: {} files ({}..{})".format(i, len(chunk), Path(chunk[0]).name, Path(chunk[-1]).name))

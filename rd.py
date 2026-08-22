import pathlib, re
p = pathlib.Path(r"C:\Users\Hi\Desktop\qna - Copy.txt")
t = p.read_text(encoding="utf-8", errors="ignore")
# extract all /queue directives
queues = re.findall(r"/queue\s+([^\n/]{10,300})", t)
seen = set()
for q in queues:
    key = q.strip()[:60].lower()
    if key in seen:
        continue
    seen.add(key)
    print("-", q.strip()[:160])
print(f"\ntotal unique: {len(seen)}")
# look for credentials.txt mention
c = pathlib.Path(r"C:\Users\Hi\Desktop\credentials.txt")
print("credentials.txt exists:", c.exists())
if c.exists():
    ct = c.read_text(encoding="utf-8", errors="ignore")
    # DO NOT print contents; just structure
    lines = [l for l in ct.splitlines() if l.strip()]
    keys = [l.split("=")[0].split(":")[0].strip() for l in lines if ("=" in l or ":" in l) and not l.strip().startswith("#")]
    print("credential keys present:", len(keys), "→", [k[:20] for k in keys[:12]])

import json, urllib.request, datetime, os

OUT = "D:/Obsidian/DhaherLabs/_jobs"
os.makedirs(OUT, exist_ok=True)
jobs = []
try:
    req = urllib.request.Request(
        "https://remotive.com/api/remote-jobs?search=python&limit=15",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    for j in data.get("jobs", []):
        jobs.append({
            "title": j.get("title"),
            "company": j.get("company_name"),
            "url": j.get("url"),
            "salary": j.get("salary"),
            "tags": j.get("tags", [])[:5],
        })
except Exception as e:
    jobs.append({"error": str(e)})

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
path = os.path.join(OUT, f"fangbot_remotive_{stamp}.json")
with open(path, "w") as f:
    json.dump(jobs, f, indent=2)
print("fangbot jobs saved:", len([x for x in jobs if 'title' in x]), "->", path)

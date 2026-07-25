import os

skills_dirs = [
    'D:/Obsidian/DhaherLabs/_full_skills/skills',
    'D:/Obsidian/DhaherLabs/_full_e/gstack',
    'D:/repositories/blackhornet/skills',
    'D:/repositories/skills',
    'E:/AI-Trader/skills',
    'E:/ai-market-maker/src/agents',
    'E:/ai-job-search',
    'C:/Users/Hi/.opencode/skill',
]
all_skills = set()
for d in skills_dirs:
    if os.path.exists(d):
        for root, dirs, files in os.walk(d):
            if 'SKILL.md' in files:
                rel = os.path.relpath(root, d)
                all_skills.add(rel)

print(f"Total skills across all locations: {len(all_skills)}")
for s in sorted(all_skills):
    print(f"  - {s}")
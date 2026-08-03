import os, sys
from collections import Counter

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
SKIP_DIRS = {
    '.git','.venv','.venv312','.venv_coint','.venv-clean','.tmp-ll-venv',
    'tmp-venv','tmp-venvv2','__pycache__','.pytest_cache','.ruff_cache',
    '.neuralmemory','graphify-out','node_modules','.circleci','.github',
    'backups','.bak','.tmp-ll-run','.agents','.claude','.opencode','.kilo',
    '.mimocode','.qoder','.zcode','.vscode','.hermes','.cursor','.opencode',
}
# heavy data dirs we tally but don't recurse deep
HEAVY = {'data','logs','results','paper_state','archive','references','docs',
         'config','tasks','scripts','tests','quant_nanggroe','dashboard','database','deploy'}

ext_counter = Counter()
files = []
MAX = 8000
walked = 0

for dirpath, dirnames, filenames in os.walk(ROOT):
    walked += 1
    # prune
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if fn in ('.gitignore',):
            pass
        ext = os.path.splitext(fn)[1].lower() or '(none)'
        ext_counter[ext] += 1
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        files.append(rel)
        if len(files) >= MAX:
            break
    if len(files) >= MAX:
        break

print("WALKED_DIRS:", walked)
print("TOTAL_FILES (capped %d):" % MAX, len(files))
print("=== EXTENSION COUNTS ===")
for ext, c in ext_counter.most_common():
    print(f"{ext:12s} {c}")

print("\n=== TOP-LEVEL DIRS ===")
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and d not in SKIP_DIRS:
        try:
            n = sum(len(f) for _,_,f in os.walk(p))
        except: n = -1
        print(f"{d:30s} ~{n} files")

# Write full list to file for later reading
out = os.path.join(ROOT, "_audit_filelist.txt")
with open(out, 'w', encoding='utf-8') as f:
    for rel in sorted(files):
        f.write(rel + "\n")
print("\nWROTE LIST ->", out)

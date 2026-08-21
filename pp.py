import pathlib
p = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree\dashboard\src\app\evolution\page.tsx")
t = p.read_text(encoding="utf-8")
n1 = t.count('variant="secondary"'); n2 = t.count('variant="outline"')
print("before:", n1, n2)

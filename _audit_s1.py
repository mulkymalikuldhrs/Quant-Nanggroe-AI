import os
from collections import Counter
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
ec = Counter()
dc = Counter()
nf = []
zb = []
tf = 0
for r,d,f in os.walk(root):
	d[:]=[x for x in d if not x.startswith(".") and x!="__pycache__" and x!=".git" and x!=".pytest_cache" and x!="node_modules"]
	for fn in f:
		if fn=="nul": continue
		tf+=1
		fp=os.path.join(r,fn)
		s=os.stat(fp)
		ext=os.path.splitext(fn)[1].lower() or "(none)"
		ec[ext]+=1
		try:
			rk=os.path.relpath(r,root)
		except:
			continue
		if rk==".": rk="(root)"
		dc[rk]+=1
		if s.st_mtime>=1767225600: nf.append((os.path.relpath(fp,root) if os.path.relpath(fp,root) else fn))
		if s.st_size==0: zb.append((os.path.relpath(fp,root) if os.path.relpath(fp,root) else fn))
print("TF="+str(tf))
print("")
print("=== EXTENSIONS ===")
for e,c in sorted(ec.items(),key=lambda x:-x[1]): print(e+" "+str(c))
print("")
print("=== TOP 30 DIRS ===")
for d,c in sorted(dc.items(),key=lambda x:-x[1])[:30]: print(str(c)+" "+d)
print("")
print("=== NEW FILES ===")
for f in sorted(set(nf)): print(f)
print("")
print("=== ZERO BYTES ===")
for f in sorted(set(zb)): print(f)

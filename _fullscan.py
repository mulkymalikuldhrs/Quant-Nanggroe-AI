import os, ast, json, sys
from collections import Counter, defaultdict

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
# Real QNA source only — exclude vendored/junk to keep scan meaningful
EXCLUDE_DIRS = {
    '.git','.venv','.venv312','.venv-clean','.venv_coint','.venv-clean','__pycache__',
    'node_modules','.hermes','.kilo','.opencode','.qoder','.claude','.cursor','.coderabbit',
    '.vscode','.zcode','.mimocode','.neuralmemory','.pytest_cache','.ruff_cache',
    '.bak','.tmp-ll-run','.tmp-ll-venv','_test312','tmp-venv','tmp-venvv2','.circleci',
    '.github','.qoder','archive','backups','references','graphify-out','quant_nanggroe_ai.egg-info',
    '.verify_venv','.venv','.venv312','.venv-clean','.venv_coint',
}
SCAN_PY_DIRS = ['quant_nanggroe','tests','scripts','config','dashboard']
SCAN_PY_ROOT = True  # root *.py (qna.py etc)
SCAN_TS = True

todo_re = __import__('re').compile(r"\b(TODO|FIXME|XXX|HACK)\b")

result = {
    'py_files':0,'py_bytes':0,'py_syntax_err':[],'stub_funcs':[],'notimpl':[],
    'todo':[],'func_count':0,'class_count':0,'ext_imports':Counter(),
    'ts_files':0,'ts_todo':[],
}
imports_internal = defaultdict(set)
imports_external = defaultdict(set)
all_mods = {}

def is_excluded(path_parts):
    return any(e in path_parts for e in EXCLUDE_DIRS)

# ---- PY scan ----
py_targets = []
for d in SCAN_PY_DIRS:
    base = os.path.join(ROOT,d)
    if not os.path.isdir(base): continue
    for dp,_,fns in os.walk(base):
        parts = dp.split(os.sep)
        if is_excluded(parts): continue
        for fn in fns:
            if fn.endswith('.py') and '__pycache__' not in dp:
                py_targets.append(os.path.join(dp,fn))
if SCAN_PY_ROOT:
    for fn in os.listdir(ROOT):
        if fn.endswith('.py'):
            py_targets.append(os.path.join(ROOT,fn))

for p in py_targets:
    result['py_files']+=1
    try: sz=os.path.getsize(p)
    except: sz=0
    result['py_bytes']+=sz
    try:
        src=open(p,encoding='utf-8',errors='replace').read()
    except Exception as e:
        open(p,encoding='utf-8',errors='replace').close()
        result['py_syntax_err'].append((p,0,f'READ_ERR {e}')); continue
    # TODO
    if todo_re.search(src):
        for i,l in enumerate(src.splitlines(),1):
            if todo_re.search(l): result['todo'].append((p,i,l.strip()[:120]))
    try:
        tree=ast.parse(src)
    except SyntaxError as e:
        result['py_syntax_err'].append((p,e.lineno,f'SYNTAX {e.msg}')); continue
    # imports
    modname = os.path.relpath(p,ROOT).replace(os.sep,'.')[:-3]
    if modname.endswith('.__init__'): modname=modname[:-9]
    all_mods[p]=modname
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            result['func_count']+=1
            body=node.body
            if len(body)==1 and isinstance(body[0],ast.Pass):
                result['stub_funcs'].append((p,node.lineno,node.name))
            elif len(body)==1 and isinstance(body[0],ast.Expr) and isinstance(getattr(body[0],'value',None),ast.Constant) and getattr(body[0].value,'value','')=='...':
                result['stub_funcs'].append((p,node.lineno,node.name+' (...)'))
        elif isinstance(node,ast.ClassDef):
            result['class_count']+=1
        elif isinstance(node,ast.Import):
            for a in node.names:
                top=a.name.split('.')[0]
                if top=='quant_nanggroe': imports_internal[modname].add(a.name)
                else: imports_external[modname].add(top)
        elif isinstance(node,ast.ImportFrom):
            if node.module and node.module.startswith('quant_nanggroe'):
                imports_internal[modname].add(node.module)
            elif node.module and not node.module.startswith('_') and not node.module.startswith('.'):
                imports_external[modname].add(node.module.split('.')[0])
    # NotImplementedError
    if 'NotImplementedError' in src:
        for i,l in enumerate(src.splitlines(),1):
            if 'NotImplementedError' in l: result['notimpl'].append((p,i,l.strip()[:120]))

# orphan detection
consumers=defaultdict(set)
for m,deps in imports_internal.items():
    for d in deps: consumers[d].add(m)
imported=set()
for d,cs in consumers.items(): imported.update([d]+list(cs))
orphans=[m for m in all_mods.values() if m not in imported and not m.endswith('__init__')]

# ---- TS/TSX scan (dashboard own code) ----
if SCAN_TS:
    for dp,_,fns in os.walk(os.path.join(ROOT,'dashboard')):
        if 'node_modules' in dp.split(os.sep): continue
        for fn in fns:
            if fn.endswith(('.ts','.tsx')) and '__pycache__' not in dp:
                result['ts_files']+=1
                try: s=open(os.path.join(dp,fn),encoding='utf-8',errors='replace').read()
                except: continue
                if todo_re.search(s):
                    for i,l in enumerate(s.splitlines(),1):
                        if todo_re.search(l): result['ts_todo'].append((os.path.join(dp,fn),i,l.strip()[:120]))

# write JSON
out={
 'summary':{
   'py_files':result['py_files'],'py_bytes':result['py_bytes'],
   'syntax_errors':len(result['py_syntax_err']),'stub_funcs':len(result['stub_funcs']),
   'notimpl':len(result['notimpl']),'todo':len(result['todo']),
   'funcs':result['func_count'],'classes':result['class_count'],
   'orphans':len(orphans),'ts_files':result['ts_files'],'ts_todo':len(result['ts_todo']),
   'unique_ext_imports':len(result['ext_imports']),
 },
 'syntax_errors':result['py_syntax_err'],
 'stub_funcs':result['stub_funcs'][:200],
 'notimpl':result['notimpl'],
 'todo':result['todo'],
 'orphans':sorted(orphans),
 'ts_todo':result['ts_todo'],
}
with open(os.path.join(ROOT,'_fullscan_result.json'),'w',encoding='utf-8') as f:
    json.dump(out,f,indent=1,default=str)
# human txt
with open(os.path.join(ROOT,'_fullscan_result.txt'),'w',encoding='utf-8') as f:
    f.write("=== FULL SCAN RESULT (code = truth) ===\n")
    f.write(f"PY files: {out['summary']['py_files']} ({out['summary']['py_bytes']} bytes)\n")
    f.write(f"Syntax errors: {out['summary']['syntax_errors']}\n")
    f.write(f"Stub funcs: {out['summary']['stub_funcs']}\n")
    f.write(f"NotImplementedError: {out['summary']['notimpl']}\n")
    f.write(f"TODO/FIXME: {out['summary']['todo']}\n")
    f.write(f"Funcs/Classes: {out['summary']['funcs']}/{out['summary']['classes']}\n")
    f.write(f"Orphans (no importer): {out['summary']['orphans']}\n")
    f.write(f"TS/TSX files: {out['summary']['ts_files']} | TS TODO: {out['summary']['ts_todo']}\n")
    f.write("\n--- SYNTAX ERRORS ---\n")
    for p,l,m in result['py_syntax_err']: f.write(f"{p}:{l} {m}\n")
    f.write("\n--- TODO/FIXME (PY) ---\n")
    for p,l,m in result['todo']: f.write(f"{p}:{l} {m}\n")
    f.write("\n--- TODO/FIXME (TS) ---\n")
    for p,l,m in result['ts_todo']: f.write(f"{p}:{l} {m}\n")
    f.write("\n--- ORPHANS ---\n")
    for o in sorted(orphans): f.write(f"{o}\n")
print("DONE py=%d ts=%d orphans=%d syntax=%d stub=%d todo=%d"%(
  out['summary']['py_files'],out['summary']['ts_files'],out['summary']['orphans'],
  out['summary']['syntax_errors'],out['summary']['stub_funcs'],out['summary']['todo']))

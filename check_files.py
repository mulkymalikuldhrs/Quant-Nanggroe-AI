import pathlib
for f in ["quant_nanggroe/config_manager.py", "quant_nanggroe/api/routes/config_files.py"]:
    p = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree") / f
    print(f, "EXISTS" if p.exists() else "MISSING")

import subprocess
import pathlib
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
r = subprocess.run(["git", "checkout", "c6888c42", "--",
                    "quant_nanggroe/engine/execution/account_discovery.py",
                    "quant_nanggroe/engine/execution/builder.py"],
                   capture_output=True, text=True, cwd=root)
print("checkout:", r.stdout, r.stderr)

# recreate local gitignored yaml if missing
y = pathlib.Path(root) / "config" / "mt5_accounts.yaml"
if not y.exists():
    y.parent.mkdir(parents=True, exist_ok=True)
    y.write_text(
        'accounts:\n'
        '  # Passwords come from .env (gitignored) via ${QNA_MT5_PASSWORD} interpolation.\n'
        '  - name: "MT5 Live-1"\n'
        '    broker: mt5\n'
        '    login: 372044706\n'
        '    server: "ValetaxIntl-Live2"\n'
        '    password: "${QNA_MT5_PASSWORD}"\n'
        '    paper: false\n',
        encoding="utf-8")
    print("yaml recreated")
else:
    print("yaml exists")

# verify
ad = pathlib.Path(root, "quant_nanggroe/engine/execution/account_discovery.py").read_text(encoding="utf-8", errors="ignore")
print("Valetax path in discovery:", "MetaTrader 5 Valetax" in ad)
bt = pathlib.Path(root, "quant_nanggroe/engine/execution/builder.py").read_text(encoding="utf-8", errors="ignore")
print("builder SKIPPED logic:", "SKIPPED" in bt)

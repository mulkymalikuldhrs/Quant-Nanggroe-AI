import pathlib
import sqlite3

root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
# 1) libs available?
for lib in ["openpyxl", "reportlab", "pandas"]:
    try:
        __import__(lib)
        print(lib, "OK")
    except ImportError:
        print(lib, "MISSING")
# 2) journal db schema
db = root / "quant_nanggroe/data/qna_trade_journal.db"
print("db exists:", db.exists())
if db.exists():
    con = sqlite3.connect(str(db))
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("tables:", tables)
    for t in tables:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})")]
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t} ({n} rows): {cols}")
    con.close()

import sqlite3, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
db = root / "quant_nanggroe/data/qna_trade_journal.db"
con = sqlite3.connect(str(db))
cur = con.cursor()
# full schema
cols = [r for r in cur.execute("PRAGMA table_info(trades)").fetchall()]
print("=== trades schema ===")
for c in cols:
    print(f"  {c[1]:20s} {c[2]:10s} pk={c[5]} notnull={c[3]}")
print(f"\nrows: {cur.execute('SELECT COUNT(*) FROM trades').fetchone()[0]}")
print("\n=== sample rows ===")
for r in cur.execute("SELECT * FROM trades LIMIT 3").fetchall():
    print(" ", dict(zip([c[1] for c in cols], r)))
print("\n=== distinct strategy values ===")
for (s,) in cur.execute("SELECT DISTINCT strategy FROM trades").fetchall():
    n = cur.execute("SELECT COUNT(*) FROM trades WHERE strategy=?", (s,)).fetchone()[0]
    print(f"  '{s}': {n}")
con.close()

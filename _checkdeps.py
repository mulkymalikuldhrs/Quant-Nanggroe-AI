import importlib.metadata as m
pkgs = ["uvicorn","polars","pytimetk","alphalens-reloaded","riskfolio-lib","chromadb",
        "langchain","langchain_core","yfinance","ccxt","torch","xgboost","gs-quant",
        "ffn","PyQL","vollib","pysabr","optlib","pytest-asyncio","pyyaml"]
for p in pkgs:
    try:
        print(f"OK   {p} {m.version(p)}")
    except Exception:
        print(f"MISS {p}")

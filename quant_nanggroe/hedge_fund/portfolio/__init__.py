"""Portfolio management: main hedge fund cycle, position oversight."""


def __getattr__(name: str):
    if name == "run_once":
        from quant_nanggroe.hedge_fund.portfolio.main import run_once as _run_once
        return _run_once
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "run_once",
]

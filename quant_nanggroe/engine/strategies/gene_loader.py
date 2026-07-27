"""Gene Loader - MUE-X Gene Discovery & Registration."""
from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

class GeneLoader:
    def __init__(self, genes_dir: Optional[str] = None):
        base = Path(__file__).resolve().parent.parent.parent
        self._genes_dir = Path(genes_dir) if genes_dir else (base / "data" / "genes")
        self._genes_dir.mkdir(parents=True, exist_ok=True)
        self._genes: dict[str, type] = {}
        logger.info("GeneLoader initialized: %s", self._genes_dir)

    def discover_genes(self) -> int:
        if not self._genes_dir.is_dir(): return 0
        discovered = 0
        for fpath in sorted(self._genes_dir.iterdir()):
            if fpath.suffix != ".py" or fpath.name == "__init__.py": continue
            mod_name = fpath.stem
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(mod_name, fpath)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                else: continue
            except Exception as exc:
                logger.debug("Skipping gene %s: %s", mod_name, exc); continue
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if obj.__module__ != mod.__name__: continue
                if name.endswith("Gene") or name.endswith("Strategy"):
                    snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")
                    self._genes[snake] = obj; discovered += 1
        logger.info("Discovered %d MUE-X genes", discovered)
        return discovered

    def register_all(self) -> int:
        return len(self._genes)
    def get_all_gene_names(self) -> list[str]:
        return list(self._genes.keys())
    def get_gene(self, name: str) -> Optional[type]:
        return self._genes.get(name)
    def get_gene_count(self) -> int:
        return len(self._genes)
    def status(self) -> dict[str, Any]:
        return {"genes_dir": str(self._genes_dir), "total_genes": len(self._genes), "gene_names": list(self._genes.keys())}

__all__ = ["GeneLoader"]

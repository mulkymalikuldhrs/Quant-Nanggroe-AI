"""AutoRegistry — Fully autonomous component registry for QNA.

Scans EVERYTHING in the entire repo. No manual __all__, no file left behind.
Auto-discovers ALL .py files across quant_nanggroe/, tests/, scripts/, root/.
Auto-generates __init__.py for directories missing them.
Auto-cleans stale registrations when files are deleted.

Usage:
    from quant_nanggroe.engine.registry import AutoRegistry
    registry = AutoRegistry()
    registry.discover_all()  # scans entire repo
    registry.health_check()
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Files to skip
_SKIP_FILES = {
    "__init__.py",
    "_df_signal_adapter.py",
    "conftest.py",
    "setup.py",
}


class AutoRegistry:
    """Fully autonomous registry — scans the ENTIRE repo.

    Every .py file in every directory is auto-discovered and registered.
    - No base_class filter — registers every class found
    - Auto-generates __init__.py for missing dirs
    - Auto-cleans stale entries on re-scan
    - File hash tracking for change detection
    - Health check with full audit
    """

    def __init__(self, repo_root: str | Path | None = None):
        self._registry: dict[str, type] = {}
        self._modules: dict[str, str] = {}
        self._file_hashes: dict[str, str] = {}
        self._scan_count: int = 0
        self._repo_root = Path(repo_root) if repo_root else self._find_repo_root()

    # ── Core Discovery ─────────────────────────────────────────────

    def discover_from_dir(
        self,
        directory: str | Path,
        base_class: Optional[type] = None,
        name_suffix: str = "",
        recursive: bool = True,
    ) -> int:
        """Scan a directory and auto-register ALL matching classes."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            logger.warning("Directory not found: %s", directory)
            return 0

        count = 0
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in sorted(dir_path.glob(pattern)):
            if py_file.name in _SKIP_FILES or py_file.name.startswith("__"):
                continue
            if any(skip in str(py_file) for skip in ("__pycache__", ".venv", "node_modules", ".next", ".git", "archive")):
                continue

            mod_name = py_file.stem
            file_hash = self._file_hash(py_file)

            # Skip unchanged files
            if mod_name in self._registry and self._file_hashes.get(mod_name) == file_hash:
                continue

            # Remove stale entry if file changed
            if mod_name in self._registry:
                del self._registry[mod_name]
                del self._modules[mod_name]

            try:
                spec = importlib.util.spec_from_file_location(mod_name, py_file)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception as e:
                logger.debug("Skipping %s: %s", py_file.name, e)
                continue

            # Register ALL classes
            for obj_name, obj in inspect.getmembers(mod, inspect.isclass):
                if obj.__module__ != mod.__name__:
                    continue
                if name_suffix and not obj_name.endswith(name_suffix):
                    continue
                if base_class is not None and not issubclass(obj, base_class):
                    continue
                if inspect.isabstract(obj):
                    continue
                if base_class is not None and obj_name == base_class.__name__:
                    continue

                key = obj_name.lower()
                self._registry[key] = obj
                self._modules[key] = str(py_file)
                self._file_hashes[key] = file_hash
                count += 1

        if count:
            logger.info("Discovered %d components in %s", count, directory)
        return count

    def discover_all(
        self,
        strategy_dirs: Optional[list[str | Path]] = None,
        base_class: Optional[type] = None,
        name_suffix: str = "",
    ) -> dict[str, int]:
        """Scan the ENTIRE repo. No directory skipped.

        Returns dict mapping directory -> number of discoveries.
        """
        if strategy_dirs is None:
            strategy_dirs = self._all_dirs()

        before = set(self._registry.keys())

        results: dict[str, int] = {}
        for d in strategy_dirs:
            n = self.discover_from_dir(d, base_class, name_suffix)
            results[str(d)] = n

        # Auto-clean stale entries
        for key in list(self._registry.keys()):
            mod_path = self._modules.get(key, "")
            if mod_path and not Path(mod_path).exists():
                del self._registry[key]
                del self._modules[key]
                self._file_hashes.pop(key, None)

        self._scan_count += 1
        return results

    # ── Auto-Init ──────────────────────────────────────────────────

    def ensure_init_files(self, root: str | Path | None = None) -> int:
        """Auto-generate __init__.py for ALL directories missing one."""
        root_path = Path(root) if root else self._repo_root
        if not root_path.is_dir():
            return 0

        created = 0
        for d in sorted(root_path.rglob("*")):
            if not d.is_dir():
                continue
            if any(skip in str(d) for skip in ("__pycache__", "node_modules", ".git", ".next", ".venv", "archive")):
                continue

            init_file = d / "__init__.py"
            if not init_file.exists():
                has_python = any(d.glob("*.py"))
                if has_python:
                    init_file.write_text(f"# {d.name} module\n")
                    created += 1
                    logger.info("Created __init__.py: %s", init_file)

        return created

    # ── Health Check ───────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """Full audit of registry health across the entire repo."""
        stale = []
        for key, mod_path in self._modules.items():
            if not Path(mod_path).exists():
                stale.append(key)

        missing_init = []
        for d in self._repo_root.rglob("*"):
            if not d.is_dir():
                continue
            if any(skip in str(d) for skip in ("__pycache__", "node_modules", ".git", ".next", ".venv", "archive")):
                continue
            has_python = any(d.glob("*.py"))
            has_init = (d / "__init__.py").exists()
            if has_python and not has_init:
                missing_init.append(str(d.relative_to(self._repo_root)))

        by_dir: dict[str, int] = {}
        for mod_path in self._modules.values():
            try:
                rel = str(Path(mod_path).relative_to(self._repo_root).parent)
                by_dir[rel] = by_dir.get(rel, 0) + 1
            except ValueError:
                by_dir["unknown"] = by_dir.get("unknown", 0) + 1

        # Count total .py files vs registered
        total_py = sum(1 for _ in self._repo_root.rglob("*.py")
                      if not any(skip in str(_) for skip in ("__pycache__", ".venv", "node_modules", ".next", ".git", "archive")))

        return {
            "total_registered": self.count(),
            "total_py_files": total_py,
            "coverage_pct": round(self.count() / max(1, total_py) * 100, 1),
            "stale": stale,
            "stale_count": len(stale),
            "missing_init": missing_init,
            "missing_init_count": len(missing_init),
            "by_directory": by_dir,
            "scan_count": self._scan_count,
        }

    # ── Access ─────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[type]:
        return self._registry.get(name.lower())

    def get_all(self) -> dict[str, type]:
        return dict(self._registry)

    def get_by_module(self, name: str) -> Optional[str]:
        return self._modules.get(name.lower())

    def list_registered(self) -> list[str]:
        return sorted(self._registry.keys())

    def count(self) -> int:
        return len(self._registry)

    # ── Internal helpers ────────────────────────────────────────────

    def _find_repo_root(self) -> Path:
        """Find repo root by looking for pyproject.toml or .git."""
        d = Path(__file__).resolve()
        while d != d.parent:
            if (d / "pyproject.toml").exists() or (d / ".git").is_dir():
                return d
            d = d.parent
        return Path(__file__).resolve().parent.parent.parent

    def _all_dirs(self) -> list[Path]:
        """Return ALL top-level directories in the repo for scanning."""
        dirs = []
        for d in sorted(self._repo_root.iterdir()):
            if not d.is_dir():
                continue
            if any(skip in str(d) for skip in (".git", ".venv", "node_modules", ".next", "__pycache__", "archive")):
                continue
            dirs.append(d)
        return dirs

    def _file_hash(self, path: Path) -> str:
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()[:12]
        except Exception:
            return "error"

    def status(self) -> dict[str, Any]:
        return {
            "total_registered": self.count(),
            "scan_count": self._scan_count,
            "components": sorted(k for k in self._registry),
        }

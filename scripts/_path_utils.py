"""Auto-detect project root — works on any OS, any drive, any path.

Usage in scripts:
    from _path_utils import PROJECT_ROOT, PROJECT_QNA
    sys.path.insert(0, str(PROJECT_ROOT))

Usage in engine code:
    from _path_utils import find_project_root
    root = find_project_root(__file__)
"""
from pathlib import Path


def find_project_root(start=None):
    """Walk up from `start` until we find pyproject.toml or .git directory."""
    p = Path(start or __file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").is_dir():
            return parent
    return p.parents[1] if len(p.parents) > 1 else p

PROJECT_ROOT = find_project_root(__file__)
PROJECT_QNA = PROJECT_ROOT / "quant_nanggroe"

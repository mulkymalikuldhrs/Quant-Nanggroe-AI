"""Generic file-backed config manager for dashboard editing.

Whitelists every editable file under ``config/`` (and the root ``config.yaml``)
so the dashboard Config Center can list / read / write them without ever
touching arbitrary paths on disk (fail-closed: path traversal → 404).

Supports YAML and JSON, validates on write, and treats mt5_accounts.yaml
as a first-class structured resource (accounts list) while still allowing
raw-text editing for any file.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── locations ───────────────────────────────────────────────────────
# config/ lives at repo root (parents[1] from quant_nanggroe/)
_REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = _REPO_ROOT / "config"
# legacy single-file config (api/routes/config.py default)
_LEGACY_CONFIG = _REPO_ROOT / "config.yaml"


@dataclass(frozen=True)
class ConfigFileDef:
    name: str          # filename exposed to the API (no directory)
    path: Path
    kind: str          # "yaml" | "json"
    description: str
    editable: bool = True


_ALLOWED: dict[str, ConfigFileDef] = {
    "mt5_accounts.yaml": ConfigFileDef(
        "mt5_accounts.yaml", CONFIG_DIR / "mt5_accounts.yaml", "yaml",
        "MT5 broker accounts — login / server / password / paper flag",
    ),
    "system_config.yaml": ConfigFileDef(
        "system_config.yaml", CONFIG_DIR / "system_config.yaml", "yaml",
        "System-wide config — core, agents, llm, database, web, logging, monitoring",
    ),
    "prompts.yaml": ConfigFileDef(
        "prompts.yaml", CONFIG_DIR / "prompts.yaml", "yaml",
        "LLM system prompts",
    ),
    "credentials.json": ConfigFileDef(
        "credentials.json", CONFIG_DIR / "credentials.json", "json",
        "Stored credentials (masked in UI; use /api/credentials for secrets)",
        editable=False,
    ),
    "config.yaml": ConfigFileDef(
        "config.yaml", _LEGACY_CONFIG, "yaml",
        "Legacy flat config (trading / strategy / execution / model / display)",
    ),
}

# ── helpers ─────────────────────────────────────────────────────────

_ENV_VAR_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _mask_secrets(data: Any) -> Any:
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            lk = k.lower()
            if any(s in lk for s in ("password", "secret", "api_key", "apikey", "token")):
                out[k] = "***" if v else v
            else:
                out[k] = _mask_secrets(v)
        return out
    if isinstance(data, list):
        return [_mask_secrets(x) for x in data]
    return data


def _load_yaml(path: Path) -> tuple[Any, str]:
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise RuntimeError("PyYAML not installed") from e
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    if not raw.strip():
        return {}, raw
    parsed = yaml.safe_load(raw)
    return parsed, raw


def _dump_yaml(data: Any) -> str:
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise RuntimeError("PyYAML not installed") from e
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _validate_mt5_accounts(data: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return ["mt5_accounts.yaml must be a mapping with key 'accounts'"]
    accs = data.get("accounts")
    if accs is None:
        return []  # empty file is allowed
    if not isinstance(accs, list):
        return ["'accounts' must be a list"]
    for i, acc in enumerate(accs):
        if not isinstance(acc, dict):
            errs.append(f"accounts[{i}] must be a mapping")
            continue
        if not acc.get("login"):
            errs.append(f"accounts[{i}].login is required")
        if not acc.get("server"):
            errs.append(f"accounts[{i}].server is required")
    return errs


def _validate_file(name: str, parsed: Any) -> list[str]:
    if name == "mt5_accounts.yaml":
        return _validate_mt5_accounts(parsed)
    # generic: must be dict or list or None
    if parsed is not None and not isinstance(parsed, (dict, list)):
        return [f"{name}: top-level must be a mapping or list"]
    return []


# ── public API ──────────────────────────────────────────────────────

def list_config_files() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, spec in _ALLOWED.items():
        p = spec.path
        exists = p.exists()
        stat = p.stat() if exists else None
        out.append({
            "name": name,
            "description": spec.description,
            "kind": spec.kind,
            "editable": spec.editable,
            "exists": exists,
            "size": stat.st_size if stat else 0,
            "modified": stat.st_mtime if stat else None,
            "path": str(p),
        })
    return out


def read_config_file(name: str, mask: bool = True) -> dict[str, Any]:
    spec = _ALLOWED.get(name)
    if spec is None:
        raise FileNotFoundError(f"Unknown config file: {name}")
    p = spec.path
    if not p.exists():
        return {"name": name, "exists": False, "raw": "", "parsed": None, "kind": spec.kind}
    if spec.kind == "yaml":
        parsed, raw = _load_yaml(p)
    else:
        raw = p.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            parsed = None
    if mask:
        parsed = _mask_secrets(parsed) if parsed is not None else parsed
    return {"name": name, "exists": True, "raw": raw, "parsed": parsed, "kind": spec.kind}


def write_config_file(name: str, raw: str | None = None, data: Any | None = None) -> dict[str, Any]:
    spec = _ALLOWED.get(name)
    if spec is None:
        raise FileNotFoundError(f"Unknown config file: {name}")
    if not spec.editable:
        raise PermissionError(f"{name} is not editable via this endpoint (use /api/credentials)")
    if raw is None and data is None:
        raise ValueError("Provide 'raw' (string) or 'data' (object)")
    # normalize to raw + parsed
    if raw is not None:
        # validate raw parses
        if spec.kind == "yaml":
            try:
                import yaml  # type: ignore
                parsed = yaml.safe_load(raw) if raw.strip() else {}
            except Exception as e:
                raise ValueError(f"Invalid YAML: {e}") from e
        else:
            try:
                parsed = json.loads(raw) if raw.strip() else {}
            except Exception as e:
                raise ValueError(f"Invalid JSON: {e}") from e
    else:
        parsed = data
        if spec.kind == "yaml":
            raw = _dump_yaml(parsed) if parsed is not None else ""
        else:
            raw = json.dumps(parsed, indent=2, ensure_ascii=False) if parsed is not None else ""

    errs = _validate_file(name, parsed)
    if errs:
        raise ValueError("; ".join(errs))

    # ensure parent exists
    spec.path.parent.mkdir(parents=True, exist_ok=True)
    # atomic write via temp + rename
    tmp = spec.path.with_suffix(spec.path.suffix + ".tmp")
    tmp.write_text(raw, encoding="utf-8")
    tmp.replace(spec.path)
    logger.info("Config file written: %s (%d bytes)", name, len(raw.encode("utf-8")))
    return {"name": name, "raw": raw, "parsed": _mask_secrets(parsed) if parsed is not None else parsed}

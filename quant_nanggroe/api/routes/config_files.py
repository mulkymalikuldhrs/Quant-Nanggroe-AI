"""Config Files API — generic file-backed config management for the dashboard.

Exposes every whitelisted file under ``config/`` (plus the legacy root
``config.yaml``) so the dashboard Config Center can list / read / write
them without manual file editing.

* ``GET  /api/config/files``            — list available config files
* ``GET  /api/config/files/{name}``     — read one file (raw + parsed)
* ``PUT  /api/config/files/{name}``     — write one file (raw or data)

Fail-closed: only whitelisted names are allowed; path traversal → 404.
``credentials.json`` is read-only via this endpoint (use ``/api/credentials``).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/config/files", tags=["config"])


class ConfigFileWrite(BaseModel):
    raw: Optional[str] = None
    data: Optional[Any] = None
    model_config = ConfigDict(extra="forbid")


@router.get("")
async def list_files() -> dict[str, Any]:
    from quant_nanggroe.config_manager import list_config_files
    return {"files": list_config_files()}


@router.get("/{name}")
async def read_file(name: str) -> dict[str, Any]:
    # block path traversal early
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(404, "Not found")
    from quant_nanggroe.config_manager import read_config_file
    try:
        return read_config_file(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@router.put("/{name}")
async def write_file(name: str, body: ConfigFileWrite) -> dict[str, Any]:
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(404, "Not found")
    if body.raw is None and body.data is None:
        raise HTTPException(400, "Provide 'raw' (string) or 'data' (object)")
    from quant_nanggroe.config_manager import write_config_file
    try:
        return write_config_file(name, raw=body.raw, data=body.data)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e

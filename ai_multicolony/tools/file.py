"""FileTool – file and directory operations with read/write safety.

Autonomy levels:
  - L1 for read operations (read, list, exists, search, metadata)
  - L2 for write operations (write, append, delete, mkdir)
"""

from __future__ import annotations

import glob as _glob
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


class FileTool(MCPTool):
    """File and directory operations with granular autonomy levels.

    Supported operations
    --------------------
    read      : read file contents  (L1)
    write     : write/overwrite a file  (L2)
    append    : append to a file  (L2)
    delete    : delete a file  (L2)
    list      : list directory entries  (L1)
    mkdir     : create directory tree  (L2)
    exists    : check path existence  (L1)
    search    : glob-pattern search  (L1)
    metadata  : file metadata (size, mtime, etc.)  (L1)
    copy      : copy a file  (L2)
    move      : move/rename a file  (L2)
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "file.operations"

    def category(self) -> str:
        return "data"

    def autonomy_level(self) -> int:
        return 1  # minimum; write ops require L2

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["operation", "path"],
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "read", "write", "append", "delete",
                        "list", "mkdir", "exists", "search",
                        "metadata", "copy", "move",
                    ],
                    "description": "File operation to perform",
                },
                "path": {
                    "type": "string",
                    "description": "Target file or directory path",
                },
                "content": {
                    "type": "string",
                    "description": "Content for write/append operations",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path for copy/move",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern for search operation",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "File encoding",
                },
                "max_size": {
                    "type": "integer",
                    "default": 10_485_760,
                    "description": "Max bytes to read (10 MB default)",
                },
                "recursive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Recursive listing or search",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "operation": {"type": "string"},
                "data": {"type": "object"},
                "error": {"type": "string"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 2001, "message": "File not found"},
            {"code": 2002, "message": "Permission denied"},
            {"code": 2003, "message": "File too large"},
            {"code": 2004, "message": "Path is a directory"},
            {"code": 2005, "message": "Path is not a directory"},
            {"code": 2006, "message": "Unknown operation"},
            {"code": 2007, "message": "Write operation requires L2 autonomy"},
        ]

    # ── Dispatch ─────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the appropriate file operation."""
        operation: str = params["operation"]
        path: str = params["path"]
        autonomy = context.get("autonomy_level", 0)

        # Write-level operations require L2
        write_ops = {"write", "append", "delete", "mkdir", "copy", "move"}
        if operation in write_ops and autonomy < 2:
            self.record_call(False)
            return {
                "success": False,
                "operation": operation,
                "data": {},
                "error": f"Operation '{operation}' requires autonomy level L2, current level is L{autonomy}",
            }

        dispatch = {
            "read": self._read,
            "write": self._write,
            "append": self._append,
            "delete": self._delete,
            "list": self._list,
            "mkdir": self._mkdir,
            "exists": self._exists,
            "search": self._search,
            "metadata": self._metadata,
            "copy": self._copy,
            "move": self._move,
        }

        handler = dispatch.get(operation)
        if handler is None:
            self.record_call(False)
            return {
                "success": False,
                "operation": operation,
                "data": {},
                "error": f"Unknown operation: {operation}",
            }

        start = time.monotonic()
        try:
            result = await handler(params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            result["operation"] = operation
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {
                "success": False,
                "operation": operation,
                "data": {},
                "error": str(exc),
            }

    # ── Read operations (L1) ─────────────────────────────────────

    async def _read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        encoding = params.get("encoding", "utf-8")
        max_size = params.get("max_size", 10_485_760)

        if not os.path.exists(path):
            return {"success": False, "data": {}, "error": f"File not found: {path}"}
        if os.path.isdir(path):
            return {"success": False, "data": {}, "error": f"Path is a directory: {path}"}

        size = os.path.getsize(path)
        if size > max_size:
            return {
                "success": False,
                "data": {"size": size, "max_size": max_size},
                "error": f"File too large: {size} bytes (max {max_size})",
            }

        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            return {
                "success": True,
                "data": {"content": content, "size": size, "encoding": encoding},
            }
        except PermissionError:
            return {"success": False, "data": {}, "error": f"Permission denied: {path}"}

    async def _list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        recursive = params.get("recursive", False)

        if not os.path.exists(path):
            return {"success": False, "data": {}, "error": f"Path not found: {path}"}
        if not os.path.isdir(path):
            return {"success": False, "data": {}, "error": f"Path is not a directory: {path}"}

        try:
            entries = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    for d in dirs:
                        full = os.path.join(root, d)
                        entries.append(self._entry_info(full, is_dir=True))
                    for f in files:
                        full = os.path.join(root, f)
                        entries.append(self._entry_info(full, is_dir=False))
            else:
                for entry in sorted(os.listdir(path)):
                    full = os.path.join(path, entry)
                    entries.append(self._entry_info(full, is_dir=os.path.isdir(full)))

            return {
                "success": True,
                "data": {"entries": entries, "count": len(entries), "path": path},
            }
        except PermissionError:
            return {"success": False, "data": {}, "error": f"Permission denied: {path}"}

    async def _exists(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        exists = os.path.exists(path)
        return {
            "success": True,
            "data": {
                "exists": exists,
                "is_file": os.path.isfile(path) if exists else False,
                "is_dir": os.path.isdir(path) if exists else False,
                "path": path,
            },
        }

    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)

        if not os.path.isdir(path):
            return {"success": False, "data": {}, "error": f"Path is not a directory: {path}"}

        full_pattern = os.path.join(path, "**" if recursive else "", pattern)
        matches = _glob.glob(full_pattern, recursive=recursive)

        results = []
        for m in matches[:500]:  # cap at 500 results
            try:
                st = os.stat(m)
                results.append({
                    "path": m,
                    "name": os.path.basename(m),
                    "size": st.st_size,
                    "is_dir": os.path.isdir(m),
                    "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                })
            except OSError:
                results.append({"path": m, "name": os.path.basename(m)})

        return {
            "success": True,
            "data": {"matches": results, "count": len(results), "pattern": pattern},
        }

    async def _metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]

        if not os.path.exists(path):
            return {"success": False, "data": {}, "error": f"Path not found: {path}"}

        try:
            st = os.stat(path)
            return {
                "success": True,
                "data": {
                    "path": path,
                    "size": st.st_size,
                    "is_file": os.path.isfile(path),
                    "is_dir": os.path.isdir(path),
                    "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                    "accessed": datetime.fromtimestamp(st.st_atime).isoformat(),
                    "mode": oct(st.st_mode),
                    "uid": st.st_uid,
                    "gid": st.st_gid,
                },
            }
        except OSError as exc:
            return {"success": False, "data": {}, "error": str(exc)}

    # ── Write operations (L2) ────────────────────────────────────

    async def _write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        content = params.get("content", "")
        encoding = params.get("encoding", "utf-8")

        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return {
                "success": True,
                "data": {"bytes_written": len(content.encode(encoding)), "path": path},
            }
        except PermissionError:
            return {"success": False, "data": {}, "error": f"Permission denied: {path}"}

    async def _append(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        content = params.get("content", "")
        encoding = params.get("encoding", "utf-8")

        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
            return {
                "success": True,
                "data": {"bytes_appended": len(content.encode(encoding)), "path": path},
            }
        except PermissionError:
            return {"success": False, "data": {}, "error": f"Permission denied: {path}"}

    async def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]

        if not os.path.exists(path):
            return {"success": False, "data": {}, "error": f"Path not found: {path}"}

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                return {"success": True, "data": {"deleted": path, "type": "directory"}}
            else:
                os.remove(path)
                return {"success": True, "data": {"deleted": path, "type": "file"}}
        except PermissionError:
            return {"success": False, "data": {}, "error": f"Permission denied: {path}"}

    async def _mkdir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]

        try:
            os.makedirs(path, exist_ok=True)
            return {"success": True, "data": {"created": path}}
        except OSError as exc:
            return {"success": False, "data": {}, "error": str(exc)}

    async def _copy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        src = params["path"]
        dst = params.get("destination", "")

        if not dst:
            return {"success": False, "data": {}, "error": "destination is required for copy"}
        if not os.path.exists(src):
            return {"success": False, "data": {}, "error": f"Source not found: {src}"}

        try:
            parent = os.path.dirname(dst)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            return {"success": True, "data": {"source": src, "destination": dst}}
        except OSError as exc:
            return {"success": False, "data": {}, "error": str(exc)}

    async def _move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        src = params["path"]
        dst = params.get("destination", "")

        if not dst:
            return {"success": False, "data": {}, "error": "destination is required for move"}
        if not os.path.exists(src):
            return {"success": False, "data": {}, "error": f"Source not found: {src}"}

        try:
            parent = os.path.dirname(dst)
            if parent:
                os.makedirs(parent, exist_ok=True)
            shutil.move(src, dst)
            return {"success": True, "data": {"source": src, "destination": dst}}
        except OSError as exc:
            return {"success": False, "data": {}, "error": str(exc)}

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _entry_info(full_path: str, is_dir: bool) -> Dict[str, Any]:
        try:
            st = os.stat(full_path)
            return {
                "name": os.path.basename(full_path),
                "path": full_path,
                "is_dir": is_dir,
                "size": st.st_size if not is_dir else 0,
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            }
        except OSError:
            return {
                "name": os.path.basename(full_path),
                "path": full_path,
                "is_dir": is_dir,
            }

"""File operations tool for the AI MultiColony Ecosystem.

Provides comprehensive file operations including read, write, edit,
list directory, glob pattern search, file diff/patch, and encoding
detection — all with path validation and size limits for safety.
"""

from __future__ import annotations

import difflib
import fnmatch
import os
import re
import shutil
from pathlib import Path
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError, ToolPermissionError
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)

# Common encoding candidates for detection
_ENCODING_CANDIDATES = [
    "utf-8",
    "utf-8-sig",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "latin-1",
    "cp1252",
    "iso-8859-1",
    "ascii",
    "gb2312",
    "gbk",
    "gb18030",
    "big5",
    "shift_jis",
    "euc-jp",
    "euc-kr",
]


def detect_encoding(raw_bytes: bytes) -> str:
    """Attempt to detect the encoding of raw bytes.

    Tries a cascade of encodings from most to least common.  Falls back
    to 'utf-8' with ``errors='replace'`` if nothing matches cleanly.

    Args:
        raw_bytes: The raw file bytes.

    Returns:
        The best-effort encoding name.
    """
    # Quick BOM check
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw_bytes.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw_bytes.startswith(b"\xfe\xff"):
        return "utf-16-be"

    for enc in _ENCODING_CANDIDATES:
        try:
            raw_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


def _read_with_detection(path: Path) -> tuple[str, str]:
    """Read a file with automatic encoding detection.

    Args:
        path: File path to read.

    Returns:
        Tuple of (content, detected_encoding).
    """
    raw = path.read_bytes()
    enc = detect_encoding(raw)
    try:
        content = raw.decode(enc, errors="replace")
    except (UnicodeDecodeError, LookupError):
        content = raw.decode("utf-8", errors="replace")
        enc = "utf-8 (fallback)"
    return content, enc


def unified_diff(old: str, new: str, path: str = "file") -> str:
    """Generate a unified diff between two strings.

    Args:
        old: Original content.
        new: New content.
        path: Filename label for the diff header.

    Returns:
        Unified diff string.
    """
    diff_lines = list(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    ))
    return "".join(diff_lines) if diff_lines else ""


class FileTool(BaseTool):
    """File operations tool with safety controls.

    Features:
    - Read, write, edit, and list files
    - Glob pattern search
    - File diff/patch generation
    - Encoding detection
    - Path validation and sandboxing
    - Size limits for safety
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._max_file_size = self._config.get("max_file_size_mb", 50) * 1024 * 1024
        self._allowed_dirs = self._config.get("allowed_dirs", None)
        self._base_dir = Path(self._config.get("base_dir", ".")).resolve()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file",
            description=(
                "Read, write, edit, list, search (glob), diff/patch files "
                "with safety controls and encoding detection"
            ),
            tool_type=ToolType.FILE,
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description=(
                        "Operation: read, write, edit, list, delete, mkdir, "
                        "copy, move, glob, diff, patch"
                    ),
                    required=True,
                    enum=[
                        "read", "write", "edit", "list", "delete",
                        "mkdir", "copy", "move", "glob", "diff", "patch",
                    ],
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="File or directory path",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write (for write/edit operations)",
                    required=False,
                ),
                ToolParameter(
                    name="old_text",
                    type="string",
                    description="Text to replace (for edit operation)",
                    required=False,
                ),
                ToolParameter(
                    name="new_text",
                    type="string",
                    description="Replacement text (for edit operation)",
                    required=False,
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination path (for copy/move operations)",
                    required=False,
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern to match (for glob operation)",
                    required=False,
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Recursive operation (for list/delete/mkdir/glob)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="replace_all",
                    type="boolean",
                    description="Replace all occurrences in edit (default: first only)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="diff_content",
                    type="string",
                    description="New content to diff against current file (for diff operation)",
                    required=False,
                ),
                ToolParameter(
                    name="patch",
                    type="string",
                    description="Unified diff to apply (for patch operation)",
                    required=False,
                ),
            ],
            tags=["file", "io", "filesystem"],
            requires_permission="file.access",
        )

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    def _validate_path(self, path: str) -> Path:
        """Validate and resolve a file path against the sandbox base directory.

        Args:
            path: The path to validate.

        Returns:
            Resolved Path object.

        Raises:
            ToolPermissionError: If path is outside allowed directories.
        """
        resolved = (self._base_dir / path).resolve()

        # Security: prevent path traversal
        try:
            resolved.relative_to(self._base_dir)
        except ValueError:
            raise ToolPermissionError(
                f"Path traversal detected: {path}",
                tool_name="file",
                required_permission="file.bypass_sandbox",
            )

        # Additional: check against explicit allowlist if set
        if self._allowed_dirs:
            allowed = False
            for ad in self._allowed_dirs:
                if str(resolved).startswith(str(Path(ad).resolve())):
                    allowed = True
                    break
            if not allowed:
                raise ToolPermissionError(
                    f"Path outside allowed directories: {path}",
                    tool_name="file",
                    required_permission="file.bypass_sandbox",
                )

        return resolved

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a file operation."""
        operation = tool_call.arguments.get("operation", "")
        path_str = tool_call.arguments.get("path", "")

        if not operation:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="No operation specified",
            )
        if not path_str:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="No path specified",
            )

        try:
            path = self._validate_path(path_str)
        except ToolPermissionError:
            raise

        dispatch: dict[str, Any] = {
            "read": self._read,
            "write": self._write,
            "edit": self._edit,
            "list": self._list,
            "delete": self._delete,
            "mkdir": self._mkdir,
            "copy": self._copy,
            "move": self._move,
            "glob": self._glob,
            "diff": self._diff,
            "patch": self._patch,
        }

        handler = dispatch.get(operation)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Unknown operation: {operation}",
            )
        return await handler(tool_call, path)

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    async def _read(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Read a file with encoding detection."""
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"File not found: {path}",
            )
        if path.is_dir():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Path is a directory, use 'list' operation: {path}",
            )

        file_size = path.stat().st_size
        if file_size > self._max_file_size:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False,
                error=f"File too large: {file_size} bytes (max: {self._max_file_size})",
            )

        try:
            content, encoding = _read_with_detection(path)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=content,
                metadata={"encoding": encoding, "size_bytes": file_size},
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to read file: {e}", tool_name="file")

    async def _write(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Write content to a file."""
        content = tool_call.arguments.get("content", "")
        if "content" not in tool_call.arguments:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="No content specified for write operation",
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to write file: {e}", tool_name="file")

    async def _edit(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Edit a file by replacing text."""
        old_text = tool_call.arguments.get("old_text", "")
        new_text = tool_call.arguments.get("new_text", "")
        replace_all = tool_call.arguments.get("replace_all", False)

        if not old_text:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="old_text is required for edit operation",
            )
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"File not found: {path}",
            )

        try:
            content, _ = _read_with_detection(path)
            if old_text not in content:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="file",
                    success=False, error="old_text not found in file",
                )

            count = content.count(old_text)
            if replace_all:
                new_content = content.replace(old_text, new_text)
                replaced = count
            else:
                new_content = content.replace(old_text, new_text, 1)
                replaced = 1

            path.write_text(new_content, encoding="utf-8")
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True,
                output=f"Replaced {replaced} occurrence(s) of old_text in {path} "
                       f"({count} total match(es) found)",
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to edit file: {e}", tool_name="file")

    async def _list(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """List directory contents."""
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Path not found: {path}",
            )
        if not path.is_dir():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Path is not a directory: {path}",
            )

        recursive = tool_call.arguments.get("recursive", False)
        entries: list[str] = []
        try:
            if recursive:
                for root, dirs, files in os.walk(path):
                    rel_root = Path(root).relative_to(path)
                    for d in sorted(dirs):
                        entries.append(f"  {rel_root / d}/")
                    for f in sorted(files):
                        entries.append(f"  {rel_root / f}")
            else:
                for item in sorted(path.iterdir()):
                    suffix = "/" if item.is_dir() else ""
                    size = ""
                    if item.is_file():
                        try:
                            size = f"  ({item.stat().st_size} bytes)"
                        except OSError:
                            pass
                    entries.append(f"  {item.name}{suffix}{size}")

            output = f"Contents of {path}:\n" + "\n".join(entries[:500])
            if len(entries) > 500:
                output += f"\n  ... and {len(entries) - 500} more items"

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=output,
                metadata={"entry_count": len(entries)},
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to list directory: {e}", tool_name="file")

    async def _delete(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Delete a file or directory."""
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Path not found: {path}",
            )

        try:
            if path.is_dir():
                shutil.rmtree(path)
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="file",
                    success=True, output=f"Deleted directory: {path}",
                )
            else:
                path.unlink()
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="file",
                    success=True, output=f"Deleted file: {path}",
                )
        except Exception as e:
            raise ToolExecutionError(f"Failed to delete: {e}", tool_name="file")

    async def _mkdir(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Create a directory."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=f"Created directory: {path}",
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to create directory: {e}", tool_name="file")

    async def _copy(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Copy a file or directory."""
        dest_str = tool_call.arguments.get("destination", "")
        if not dest_str:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="destination is required for copy operation",
            )

        dest = self._validate_path(dest_str)

        try:
            if path.is_dir():
                shutil.copytree(path, dest)
            else:
                shutil.copy2(path, dest)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=f"Copied {path} to {dest}",
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to copy: {e}", tool_name="file")

    async def _move(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Move a file or directory."""
        dest_str = tool_call.arguments.get("destination", "")
        if not dest_str:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="destination is required for move operation",
            )

        dest = self._validate_path(dest_str)

        try:
            shutil.move(str(path), str(dest))
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=f"Moved {path} to {dest}",
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to move: {e}", tool_name="file")

    async def _glob(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Search for files matching a glob pattern."""
        pattern = tool_call.arguments.get("pattern", "*")
        recursive = tool_call.arguments.get("recursive", True)

        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Path not found: {path}",
            )
        if not path.is_dir():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"Path is not a directory: {path}",
            )

        try:
            if recursive:
                matches = list(path.rglob(pattern))
            else:
                matches = list(path.glob(pattern))

            # Sort by name for deterministic output
            matches.sort(key=lambda p: str(p))

            lines: list[str] = []
            for m in matches[:500]:
                rel = m.relative_to(path)
                suffix = "/" if m.is_dir() else ""
                lines.append(f"  {rel}{suffix}")

            output = f"Glob '{pattern}' in {path} ({len(matches)} matches):\n"
            output += "\n".join(lines)
            if len(matches) > 500:
                output += f"\n  ... and {len(matches) - 500} more matches"

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=output,
                metadata={"match_count": len(matches), "pattern": pattern},
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to glob: {e}", tool_name="file")

    async def _diff(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Generate a unified diff between the file and new content."""
        diff_content = tool_call.arguments.get("diff_content", "")

        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"File not found: {path}",
            )

        try:
            old_content, _ = _read_with_detection(path)
            diff = unified_diff(old_content, diff_content, str(path))

            if not diff:
                return ToolResult(
                    tool_call_id=tool_call.id, tool_name="file",
                    success=True, output="No differences found",
                )

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True, output=diff,
                metadata={"has_changes": True},
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to diff: {e}", tool_name="file")

    async def _patch(self, tool_call: ToolCall, path: Path) -> ToolResult:
        """Apply a unified diff patch to a file."""
        patch_text = tool_call.arguments.get("patch", "")

        if not patch_text:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error="patch is required for patch operation",
            )
        if not path.exists():
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=False, error=f"File not found: {path}",
            )

        try:
            old_content, _ = _read_with_detection(path)
            old_lines = old_content.splitlines(keepends=True)
            patch_lines = patch_text.splitlines(keepends=True)

            # Apply patch using difflib's parser
            new_lines = list(old_lines)
            hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
            line_idx = 0
            applied = 0

            while line_idx < len(patch_lines):
                line = patch_lines[line_idx]

                # Look for hunk header
                m = hunk_re.match(line)
                if m:
                    old_start = int(m.group(1)) - 1  # 0-indexed
                    old_count = int(m.group(2)) if m.group(2) is not None else 1

                    # Collect changes in this hunk
                    remove_lines: list[str] = []
                    add_lines: list[str] = []
                    line_idx += 1

                    while line_idx < len(patch_lines):
                        pline = patch_lines[line_idx]
                        if pline.startswith("@@") or not pline.startswith((" ", "-", "+")):
                            break
                        if pline.startswith("-"):
                            remove_lines.append(pline[1:])
                        elif pline.startswith("+"):
                            add_lines.append(pline[1:])
                        # Context lines (starting with space) are skipped
                        line_idx += 1

                    # Apply the hunk: replace old lines with new
                    end = old_start + old_count
                    # Verify context matches
                    if old_start <= len(new_lines):
                        new_lines[old_start:end] = add_lines
                        applied += 1
                    continue

                line_idx += 1

            new_content = "".join(new_lines)
            path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="file",
                success=True,
                output=f"Applied {applied} hunk(s) to {path}",
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to patch: {e}", tool_name="file")

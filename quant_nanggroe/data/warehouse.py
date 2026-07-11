"""Parquet-based data warehouse for paper run data.

Stores cycles, attribution, metrics, regimes, and positions
as partitioned Parquet files for efficient storage and query.
"""

import logging
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_nanggroe.engine.monitor_hub import MetricSnapshot

logger = logging.getLogger(__name__)

_PARQUET_MAGIC = b"PAR1"

# Thrift Compact Protocol type codes (from apache thrift TCompactProtocol)
_CT_STOP = 0
_CT_I32 = 5
_CT_I64 = 6
_CT_DOUBLE = 7
_CT_BINARY = 8
_CT_LIST = 9
_CT_STRUCT = 12

# Parquet physical types
_PQ_INT32 = 1
_PQ_INT64 = 2
_PQ_DOUBLE = 5
_PQ_BYTE_ARRAY = 6

_TABLE_SCHEMAS: dict[str, list[tuple[str, int]]] = {
    "cycles": [
        ("timestamp", _PQ_BYTE_ARRAY),
        ("cycle_number", _PQ_INT64),
        ("equity", _PQ_DOUBLE),
        ("cash", _PQ_DOUBLE),
        ("total_value", _PQ_DOUBLE),
        ("unrealized_pnl", _PQ_DOUBLE),
        ("realized_pnl", _PQ_DOUBLE),
        ("drawdown_pct", _PQ_DOUBLE),
        ("regime", _PQ_BYTE_ARRAY),
        ("num_positions", _PQ_INT64),
        ("error_rate", _PQ_DOUBLE),
    ],
    "attribution": [
        ("timestamp", _PQ_BYTE_ARRAY),
        ("cycle_number", _PQ_INT64),
        ("symbol", _PQ_BYTE_ARRAY),
        ("strategy", _PQ_BYTE_ARRAY),
        ("unrealized_pnl", _PQ_DOUBLE),
        ("realized_pnl", _PQ_DOUBLE),
        ("entry_price", _PQ_DOUBLE),
        ("current_price", _PQ_DOUBLE),
        ("position_qty", _PQ_DOUBLE),
        ("regime_at_entry", _PQ_BYTE_ARRAY),
    ],
    "metrics": [
        ("timestamp", _PQ_BYTE_ARRAY),
        ("cycle_number", _PQ_INT64),
        ("execution_latency_ms", _PQ_DOUBLE),
        ("error_rate", _PQ_DOUBLE),
        ("signal_freshness_sec", _PQ_DOUBLE),
        ("pnl_per_cycle", _PQ_DOUBLE),
        ("risk_score", _PQ_DOUBLE),
        ("correlation", _PQ_DOUBLE),
        ("system_health", _PQ_DOUBLE),
    ],
    "regimes": [
        ("timestamp", _PQ_BYTE_ARRAY),
        ("cycle_number", _PQ_INT64),
        ("regime", _PQ_BYTE_ARRAY),
        ("confidence", _PQ_DOUBLE),
        ("risk_multiplier", _PQ_DOUBLE),
    ],
    "positions": [
        ("timestamp", _PQ_BYTE_ARRAY),
        ("cycle_number", _PQ_INT64),
        ("symbol", _PQ_BYTE_ARRAY),
        ("side", _PQ_BYTE_ARRAY),
        ("qty", _PQ_DOUBLE),
        ("entry_price", _PQ_DOUBLE),
        ("current_price", _PQ_DOUBLE),
        ("unrealized_pnl", _PQ_DOUBLE),
    ],
}

_PARQUET_TYPES = list(_TABLE_SCHEMAS.keys())


# ═══════════════════════════════════════════════════════════════════════════
#  Thrift Compact Protocol encoder
# ═══════════════════════════════════════════════════════════════════════════

def _uvarint(data: bytes, offset: int = 0) -> tuple[int, int]:
    result = 0
    shift = 0
    i = offset
    while i < len(data):
        byte = data[i]
        result |= (byte & 0x7F) << shift
        shift += 7
        i += 1
        if not (byte & 0x80):
            break
    return result, i - offset


def _enc_uvarint(n: int) -> bytes:
    buf = bytearray()
    while n > 0x7F:
        buf.append((n & 0x7F) | 0x80)
        n >>= 7
    buf.append(n & 0x7F)
    return bytes(buf)


def _zigzag32(n: int) -> int:
    return (n << 1) ^ (n >> 31)


def _unzigzag32(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def _zigzag64(n: int) -> int:
    return (n << 1) ^ (n >> 63)


def _unzigzag64(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def _enc_field_header(fid: int, ctype: int) -> bytes:
    if fid <= 15:
        return bytes([(fid << 4) | ctype])
    return bytes([ctype]) + _enc_uvarint(fid)


def _enc_list_header(size: int, elem_ctype: int) -> bytes:
    if size <= 14:
        return bytes([(size << 4) | elem_ctype])
    return bytes([(0x0F << 4) | elem_ctype]) + _enc_uvarint(size)


# ── Primitive value encoders ──────────────────────────────────────────


def _enc_i32(n: int) -> bytes:
    return _enc_uvarint(_zigzag32(n))


def _enc_i64(n: int) -> bytes:
    return _enc_uvarint(_zigzag64(n))


def _enc_double(n: float) -> bytes:
    return struct.pack("<d", n)


def _enc_binary(s: str | bytes) -> bytes:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return _enc_uvarint(len(s)) + s


def _enc_stop() -> bytes:
    return b"\x00"


# ── Schema element writer ─────────────────────────────────────────────


def _write_schema_element(name: str, pq_type: int, num_children: int = 0) -> bytes:
    parts = [_enc_field_header(1, _CT_BINARY), _enc_binary(name)]
    parts += [_enc_field_header(4, _CT_I32), _enc_i32(0)]  # REQUIRED
    if num_children > 0:
        parts += [_enc_field_header(5, _CT_I32), _enc_i32(num_children)]
    else:
        parts += [_enc_field_header(2, _CT_I32), _enc_i32(pq_type)]
    parts.append(_enc_stop())
    return b"".join(parts)


def _write_root_schema(num_children: int) -> bytes:
    return b"".join([
        _enc_field_header(1, _CT_BINARY), _enc_binary(b""),
        _enc_field_header(5, _CT_I32), _enc_i32(num_children),
        _enc_stop(),
    ])


# ── DataPageHeader ────────────────────────────────────────────────────


def _write_data_page_header(num_values: int) -> bytes:
    return b"".join([
        _enc_field_header(1, _CT_I32), _enc_i32(num_values),
        _enc_field_header(2, _CT_I32), _enc_i32(0),  # PLAIN
        _enc_field_header(3, _CT_I32), _enc_i32(0),  # PLAIN def
        _enc_field_header(4, _CT_I32), _enc_i32(0),  # PLAIN rep
        _enc_stop(),
    ])


# ── PageHeader ────────────────────────────────────────────────────────


def _write_page_header(num_values: int, uncompressed_size: int) -> bytes:
    return b"".join([
        _enc_field_header(1, _CT_I32), _enc_i32(0),  # DATA_PAGE
        _enc_field_header(2, _CT_I32), _enc_i32(uncompressed_size),
        _enc_field_header(3, _CT_I32), _enc_i32(uncompressed_size),
        _enc_field_header(5, _CT_STRUCT),
        _write_data_page_header(num_values),
        _enc_stop(),
    ])


# ── ColumnMetaData ────────────────────────────────────────────────────


def _write_column_meta(
    pq_type: int, path: list[str], num_values: int,
    uncompressed_size: int, data_page_offset: int,
) -> bytes:
    parts = [
        _enc_field_header(1, _CT_I32), _enc_i32(pq_type),
        _enc_field_header(2, _CT_LIST),
        _enc_list_header(1, _CT_I32), _enc_i32(0),
        _enc_field_header(3, _CT_LIST),
        _enc_list_header(len(path), _CT_BINARY),
    ]
    for p in path:
        parts.append(_enc_binary(p))
    parts += [
        _enc_field_header(4, _CT_I32), _enc_i32(0),  # UNCOMPRESSED
        _enc_field_header(5, _CT_I64), _enc_i64(num_values),
        _enc_field_header(6, _CT_I64), _enc_i64(uncompressed_size),
        _enc_field_header(7, _CT_I64), _enc_i64(uncompressed_size),
        _enc_field_header(9, _CT_I64), _enc_i64(data_page_offset),
        _enc_stop(),
    ]
    return b"".join(parts)


# ── ColumnChunk ───────────────────────────────────────────────────────


def _write_column_chunk(
    pq_type: int, path: list[str], num_values: int,
    data_size: int, file_offset: int,
) -> bytes:
    return b"".join([
        _enc_field_header(2, _CT_I64), _enc_i64(file_offset),
        _enc_field_header(3, _CT_STRUCT),
        _write_column_meta(pq_type, path, num_values, data_size, file_offset),
        _enc_stop(),
    ])


# ── RowGroup ──────────────────────────────────────────────────────────


def _write_row_group(columns: list[bytes], num_rows: int, total_size: int) -> bytes:
    parts = [
        _enc_field_header(1, _CT_LIST),
        _enc_list_header(len(columns), _CT_STRUCT),
    ]
    parts.extend(columns)
    parts += [
        _enc_field_header(2, _CT_I64), _enc_i64(total_size),
        _enc_field_header(3, _CT_I64), _enc_i64(num_rows),
        _enc_stop(),
    ]
    return b"".join(parts)


# ── PLAIN encoding ────────────────────────────────────────────────────


def _encode_plain_column(values: list, pq_type: int) -> bytes:
    buf = bytearray()
    for v in values:
        if pq_type == _PQ_BYTE_ARRAY:
            s = str(v).encode("utf-8") if not isinstance(v, bytes) else v
            buf.extend(struct.pack("<i", len(s)))
            buf.extend(s)
        elif pq_type == _PQ_INT64:
            buf.extend(struct.pack("<q", int(v)))
        elif pq_type == _PQ_INT32:
            buf.extend(struct.pack("<i", int(v)))
        elif pq_type == _PQ_DOUBLE:
            buf.extend(struct.pack("<d", float(v)))
    return bytes(buf)


# ═══════════════════════════════════════════════════════════════════════════
#  Full Parquet file builder
# ═══════════════════════════════════════════════════════════════════════════

def _build_parquet(table: str, rows: list[dict]) -> bytes:
    schema = _TABLE_SCHEMAS[table]
    num_cols = len(schema)
    root = _write_root_schema(num_cols)
    col_schemas = [_write_schema_element(name, pqt) for name, pqt in schema]

    column_data: list[list] = [[] for _ in range(num_cols)]
    for row in rows:
        for i, (name, _) in enumerate(schema):
            column_data[i].append(row.get(name))

    num_rows = len(rows)
    col_chunks: list[bytes] = []
    data_offset = 4

    for i, (name, pqt) in enumerate(schema):
        raw = _encode_plain_column(column_data[i], pqt)
        ph = _write_page_header(num_rows, len(raw))
        page_data = ph + raw
        data_size = len(page_data)

        chunk = _write_column_chunk(pqt, [name], num_rows, data_size, data_offset)
        col_chunks.append(chunk)
        data_offset += data_size

    total_size = data_offset - 4
    rg = _write_row_group(col_chunks, num_rows, total_size)

    fm_parts = [
        _enc_field_header(1, _CT_I32), _enc_i32(1),
        _enc_field_header(2, _CT_LIST),
        _enc_list_header(1 + num_cols, _CT_STRUCT),
    ]
    fm_parts.extend([root] + col_schemas)
    fm_parts += [
        _enc_field_header(3, _CT_I64), _enc_i64(num_rows),
        _enc_field_header(4, _CT_LIST),
        _enc_list_header(1, _CT_STRUCT),
        rg,
        _enc_field_header(6, _CT_BINARY), _enc_binary("quant-nanggroe-warehouse"),
        _enc_stop(),
    ]
    footer = b"".join(fm_parts)

    out = bytearray()
    out.extend(_PARQUET_MAGIC)
    for i in range(num_cols):
        raw = _encode_plain_column(column_data[i], schema[i][1])
        ph = _write_page_header(num_rows, len(raw))
        out.extend(ph)
        out.extend(raw)
    out.extend(footer)
    out.extend(struct.pack("<i", len(footer)))
    out.extend(_PARQUET_MAGIC)
    return bytes(out)


# ═══════════════════════════════════════════════════════════════════════════
#  Pure-Python Parquet reader
# ═══════════════════════════════════════════════════════════════════════════

def _get_num(d: dict, key: str, default: float = 0) -> int | float:
    v = d.get(key, default)
    return v if isinstance(v, (int, float)) else default


def _normalize_struct(d: dict) -> dict:
    if not d:
        return d

    is_list = lambda v: isinstance(v, list)

    # RowGroup: field_1 is a list of structs
    if is_list(d.get("field_1")) and "field_3" in d:
        cols = [_normalize_struct(c) for c in d["field_1"] if isinstance(c, dict)]
        return {"columns": cols, "total_byte_size": d.get("field_2", 0),
                "num_rows": d.get("field_3", 0)}

    # ColumnChunk: field_2=file_offset, field_3=meta_data (dict)
    if "field_2" in d and isinstance(d.get("field_3"), dict):
        return {"file_offset": d["field_2"], "meta_data": _normalize_struct(d["field_3"])}

    # ColumnMetaData: has field_6 (total_uncompressed_size)
    if "field_6" in d:
        return {
            "type": d.get("field_1", 0),
            "encodings": d.get("field_2", []),
            "path_in_schema": d.get("field_3", []),
            "codec": d.get("field_4", 0),
            "num_values": d.get("field_5", 0),
            "total_uncompressed_size": d.get("field_6", 0),
            "total_compressed_size": d.get("field_7", 0),
            "data_page_offset": d.get("field_9", 0),
        }

    # SchemaElement: has field_4 (repetition_type)
    if "field_4" in d:
        is_leaf = "field_2" in d
        return {
            "name": d.get("field_1", ""),
            "type": d.get("field_2", 0) if is_leaf else None,
            "repetition_type": d.get("field_4", 0),
            "num_children": d.get("field_5", 0) if not is_leaf else 0,
        }

    return d


def _read_parquet(path: Path) -> pd.DataFrame:
    data = path.read_bytes()
    if data[:4] != _PARQUET_MAGIC or data[-4:] != _PARQUET_MAGIC:
        raise ValueError(f"Not a valid Parquet file: {path}")

    meta_len = struct.unpack_from("<i", data, len(data) - 8)[0]
    footer_start = len(data) - 8 - meta_len
    footer = data[footer_start:footer_start + meta_len]

    result, _ = _cp_read_struct(footer, 0, {
        1: "version", 2: "schema", 3: "num_rows", 4: "row_groups", 6: "created_by",
    })
    raw_row_groups = result.get("row_groups", [])
    if not raw_row_groups:
        return pd.DataFrame()

    records = []
    for rg_raw in raw_row_groups:
        rg = _normalize_struct(rg_raw)
        if not rg:
            continue
        raw_columns = rg.get("columns", [])
        nrows = _get_num(rg, "num_rows", 0)
        if not raw_columns or nrows == 0:
            continue

        col_info: list[tuple[str, int, int, int]] = []
        for chunk_raw in raw_columns:
            chunk = _normalize_struct(chunk_raw)
            if not chunk:
                continue
            cmeta_raw = chunk.get("meta_data", chunk)
            cmeta = _normalize_struct(cmeta_raw) if isinstance(cmeta_raw, dict) else {}
            path_arr = cmeta.get("path_in_schema", [""])
            if isinstance(path_arr, list) and len(path_arr) > 0:
                cname = str(path_arr[0])
            else:
                cname = ""
            ctype = _get_num(cmeta, "type", 0)
            offset = _get_num(chunk, "file_offset", 0)
            size = _get_num(cmeta, "total_uncompressed_size", 0)
            if cname:
                col_info.append((cname, ctype, offset, size))

        for row_idx in range(nrows):
            record: dict[str, Any] = {}
            for cname, ctype, coff, csize in col_info:
                val = _read_plain_value(data, coff, ctype, row_idx, nrows)
                if val is not None:
                    record[cname] = val
            records.append(record)

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def _read_plain_value(
    data: bytes, col_start: int, pq_type: int, row_idx: int, num_rows: int,
) -> Any:
    pos = _skip_page_header(data, col_start)
    for r in range(num_rows):
        if pq_type == _PQ_BYTE_ARRAY:
            if pos + 4 > len(data):
                return None
            length = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            if pos + length > len(data):
                return None
            val = data[pos:pos + length].decode("utf-8", errors="replace")
            pos += length
            if r == row_idx:
                return val
        elif pq_type in (_PQ_INT64,):
            if pos + 8 > len(data):
                return None
            val = struct.unpack_from("<q", data, pos)[0]
            pos += 8
            if r == row_idx:
                return val
        elif pq_type == _PQ_INT32:
            if pos + 4 > len(data):
                return None
            val = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            if r == row_idx:
                return val
        elif pq_type == _PQ_DOUBLE:
            if pos + 8 > len(data):
                return None
            val = struct.unpack_from("<d", data, pos)[0]
            pos += 8
            if r == row_idx:
                return val
        else:
            return None
    return None


def _skip_page_header(data: bytes, offset: int) -> int:
    _, end = _cp_read_struct(data, offset, {})
    return end


# ═══════════════════════════════════════════════════════════════════════════
#  Thrift Compact Protocol decoder
# ═══════════════════════════════════════════════════════════════════════════

def _cp_skip_field(data: bytes, offset: int, ctype: int) -> int:
    if ctype == _CT_STOP or ctype in (1, 2, 3, 4):
        return offset if ctype == _CT_STOP else offset + 1
    if ctype in (_CT_I32, _CT_I64):
        _, n = _uvarint(data, offset)
        return offset + n
    if ctype == _CT_DOUBLE:
        return offset + 8
    if ctype == _CT_BINARY:
        length, n = _uvarint(data, offset)
        return offset + n + length
    if ctype == _CT_LIST:
        return _cp_skip_list(data, offset)
    if ctype == _CT_STRUCT:
        _, end = _cp_read_struct(data, offset, {})
        return end
    return offset


def _cp_skip_list(data: bytes, offset: int) -> int:
    if offset >= len(data):
        return offset
    header = data[offset]
    elem_ctype = header & 0x0F
    size = header >> 4
    pos = offset + 1
    if size == 15:
        sz, n = _uvarint(data, pos)
        size = 15 + sz
        pos += n
    for _ in range(size):
        if elem_ctype == _CT_STRUCT:
            _, pos = _cp_read_struct(data, pos, {})
        else:
            pos = _cp_skip_field(data, pos, elem_ctype)
    return pos


def _cp_read_struct(
    data: bytes, offset: int, fields: dict[int, str],
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    pos = offset
    while pos < len(data):
        header = data[pos]
        ctype = header & 0x0F
        if ctype == _CT_STOP:
            return result, pos + 1
        fid = header >> 4
        pos += 1
        if fid == 0 and ctype != _CT_STOP:
            ff, n = _uvarint(data, pos)
            fid = ff
            pos += n
        name = fields.get(fid)
        if name is None:
            name = f"field_{fid}"
        if ctype == _CT_I32:
            val, n = _uvarint(data, pos)
            result[name] = _unzigzag32(val)
            pos += n
        elif ctype == _CT_I64:
            val, n = _uvarint(data, pos)
            result[name] = _unzigzag64(val)
            pos += n
        elif ctype == _CT_DOUBLE:
            if pos + 8 > len(data):
                break
            result[name] = struct.unpack_from("<d", data, pos)[0]
            pos += 8
        elif ctype == _CT_BINARY:
            length, n = _uvarint(data, pos)
            pos += n
            if pos + length > len(data):
                break
            result[name] = data[pos:pos + length].decode("utf-8", errors="replace")
            pos += length
        elif ctype == _CT_LIST:
            items, pos = _cp_read_list(data, pos)
            result[name] = items
        elif ctype == _CT_STRUCT:
            sub, pos = _cp_read_struct(data, pos, {})
            result[name] = sub
        else:
            pos = _cp_skip_field(data, pos, ctype)
    return result, pos


def _cp_read_list(data: bytes, offset: int) -> tuple[list, int]:
    if offset >= len(data):
        return [], offset
    header = data[offset]
    elem_ctype = header & 0x0F
    size = header >> 4
    pos = offset + 1
    if size == 15:
        sz, n = _uvarint(data, pos)
        size = 15 + sz
        pos += n
    items: list = []
    for _ in range(size):
        if elem_ctype == _CT_STRUCT:
            sub, pos = _cp_read_struct(data, pos, {})
            items.append(sub)
        elif elem_ctype == _CT_I32:
            val, n = _uvarint(data, pos)
            items.append(_unzigzag32(val))
            pos += n
        elif elem_ctype == _CT_I64:
            val, n = _uvarint(data, pos)
            items.append(_unzigzag64(val))
            pos += n
        elif elem_ctype == _CT_DOUBLE:
            if pos + 8 > len(data):
                break
            items.append(struct.unpack_from("<d", data, pos)[0])
            pos += 8
        elif elem_ctype == _CT_BINARY:
            length, n = _uvarint(data, pos)
            pos += n
            if pos + length > len(data):
                break
            items.append(data[pos:pos + length].decode("utf-8", errors="replace"))
            pos += length
        else:
            pos = _cp_skip_field(data, pos, elem_ctype)
            items.append(None)
    return items, pos


# ═══════════════════════════════════════════════════════════════════════════
#  DataWarehouse
# ═══════════════════════════════════════════════════════════════════════════

class DataWarehouse:
    """Parquet-based data warehouse for paper run data.

    Stores cycles, attribution, metrics, regimes, and positions
    as partitioned Parquet files for efficient query and analysis.
    """

    def __init__(self, state_dir: str | Path):
        self._base = Path(state_dir) / "warehouse"
        self._base.mkdir(parents=True, exist_ok=True)
        self._paths = {t: self._base / f"{t}.parquet" for t in _PARQUET_TYPES}

    def write_cycle(self, data: dict) -> None:
        ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
        row = {
            "timestamp": ts,
            "cycle_number": int(data.get("cycle", 0)),
            "equity": float(data.get("equity", 0.0)),
            "cash": float(data.get("cash", 0.0)),
            "total_value": float(data.get("total_value", 0.0)),
            "unrealized_pnl": float(data.get("unrealized_pnl", 0.0)),
            "realized_pnl": float(data.get("realized_pnl", 0.0)),
            "drawdown_pct": float(data.get("drawdown_pct", 0.0)),
            "regime": str(data.get("regime", "unknown")),
            "num_positions": int(data.get("positions", 0)),
            "error_rate": float(data.get("error_rate", 0.0)),
        }
        self._append("cycles", row)

    def write_attribution(self, rows: list[dict]) -> None:
        if not rows:
            return
        mapped = []
        for r in rows:
            mapped.append({
                "timestamp": str(r.get("timestamp", datetime.now(timezone.utc).isoformat())),
                "cycle_number": int(r.get("cycle", r.get("cycle_number", 0))),
                "symbol": str(r.get("symbol", "")),
                "strategy": str(r.get("strategy", "")),
                "unrealized_pnl": float(r.get("unrealized_pnl", 0.0)),
                "realized_pnl": float(r.get("realized_pnl", 0.0)),
                "entry_price": float(r.get("entry_price", 0.0)),
                "current_price": float(r.get("current_price", 0.0)),
                "position_qty": float(r.get("position_qty", 0.0)),
                "regime_at_entry": str(r.get("regime_at_entry", "unknown")),
            })
        self._append_batch("attribution", mapped)

    def write_metrics(self, snapshot: MetricSnapshot) -> None:
        row = {
            "timestamp": snapshot.timestamp or datetime.now(timezone.utc).isoformat(),
            "cycle_number": int(snapshot.cycle_count),
            "execution_latency_ms": float(snapshot.execution_latency_ms),
            "error_rate": float(snapshot.error_rate),
            "signal_freshness_sec": float(snapshot.signal_freshness_sec),
            "pnl_per_cycle": float(snapshot.pnl_per_cycle),
            "risk_score": float(snapshot.risk_score),
            "correlation": float(snapshot.correlation),
            "system_health": float(snapshot.system_health),
        }
        self._append("metrics", row)

    def write_regime(self, data: dict) -> None:
        row = {
            "timestamp": data.get("detected_at", datetime.now(timezone.utc).isoformat()),
            "cycle_number": int(data.get("cycle_number", 0)),
            "regime": str(data.get("regime", "unknown")),
            "confidence": float(data.get("confidence", 0.0)),
            "risk_multiplier": float(data.get("risk_multiplier", 1.0)),
        }
        self._append("regimes", row)

    def write_positions(self, positions: list[dict]) -> None:
        if not positions:
            return
        mapped = []
        for p in positions:
            if isinstance(p, dict):
                mapped.append({
                    "timestamp": str(p.get("timestamp", datetime.now(timezone.utc).isoformat())),
                    "cycle_number": int(p.get("cycle_number", 0)),
                    "symbol": str(p.get("symbol", "")),
                    "side": str(p.get("side", "")),
                    "qty": float(p.get("qty", p.get("quantity", p.get("position_qty", 0.0)))),
                    "entry_price": float(p.get("entry_price", 0.0)),
                    "current_price": float(p.get("current_price", 0.0)),
                    "unrealized_pnl": float(p.get("unrealized_pnl", 0.0)),
                })
        self._append_batch("positions", mapped)

    def _append(self, table: str, row: dict) -> None:
        self._append_batch(table, [row])

    def _append_batch(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        path = self._paths[table]
        existing_rows: list[dict] = []
        if path.exists():
            try:
                df = _read_parquet(path)
                existing_rows = df.to_dict("records") if not df.empty else []
            except Exception:
                pass
        all_rows = existing_rows + rows
        data = _build_parquet(table, all_rows)
        with open(path, "wb") as f:
            f.write(data)

    def query(
        self,
        table: str,
        start_date: str | None = None,
        end_date: str | None = None,
        symbols: list[str] | None = None,
    ) -> pd.DataFrame:
        path = self._paths.get(table)
        if not path or not path.exists():
            return pd.DataFrame()
        try:
            df = _read_parquet(path)
        except Exception:
            return pd.DataFrame()
        if start_date and "timestamp" in df.columns:
            df = df[df["timestamp"] >= start_date]
        if end_date and "timestamp" in df.columns:
            df = df[df["timestamp"] <= end_date]
        if symbols and "symbol" in df.columns:
            df = df[df["symbol"].isin(symbols)]
        return df

    def summary(self) -> dict:
        info: dict[str, Any] = {}
        for t in _PARQUET_TYPES:
            path = self._paths.get(t)
            if not path or not path.exists():
                info[t] = {"rows": 0}
                continue
            try:
                df = _read_parquet(path)
                ts_col = df["timestamp"] if "timestamp" in df.columns else None
                info[t] = {
                    "rows": len(df),
                    "start": str(ts_col.min()) if ts_col is not None and len(df) > 0 else None,
                    "end": str(ts_col.max()) if ts_col is not None and len(df) > 0 else None,
                    "size_bytes": path.stat().st_size,
                }
            except Exception as e:
                info[t] = {"rows": 0, "error": str(e)}
        return info

    def close(self) -> None:
        pass

"""Parse uploaded files into a tabular dataset and apply real filters/compare."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class Dataset:
    filename: str
    columns: list[str]
    rows: list[dict[str, Any]]
    numeric_columns: list[str] = field(default_factory=list)
    date_column: str | None = None
    text_preview: str = ""

    def metrics(self) -> list[dict[str, Any]]:
        """Derive metric cards from numeric columns (mean of filtered rows)."""
        cards = []
        for col in self.numeric_columns[:8]:
            values = [float(r[col]) for r in self.rows if _is_number(r.get(col))]
            if not values:
                continue
            total = sum(values)
            avg = total / len(values)
            cards.append({
                "id": _slug(col),
                "label": col,
                "type": "metric_card",
                "value": _fmt(avg if abs(avg) < 1e6 else total),
                "numeric_value": avg,
                "column": col,
                "change": f"n={len(values)}",
            })
        return cards


def parse_upload(filename: str, raw: bytes) -> Dataset:
    name = filename.lower()
    text = raw.decode("utf-8-sig", errors="replace")
    if name.endswith(".json"):
        return _from_json(filename, text)
    if name.endswith(".csv") or name.endswith(".tsv"):
        delim = "\t" if name.endswith(".tsv") else ","
        return _from_csv(filename, text, delim)
    # plain text / unknown: wrap as one-column notes
    rows = [{"content": line} for line in text.splitlines() if line.strip()][:500]
    return Dataset(
        filename=filename,
        columns=["content"],
        rows=rows,
        numeric_columns=[],
        date_column=None,
        text_preview=text[:8000],
    )


def apply_filter(ds: Dataset, spec: dict[str, Any] | None) -> Dataset:
    if not spec or not ds.rows:
        return ds
    rows = list(ds.rows)
    days = spec.get("last_n_days")
    if days and ds.date_column:
        cutoff = datetime.utcnow() - timedelta(days=int(days))
        kept = []
        for r in rows:
            dt = _parse_date(r.get(ds.date_column))
            if dt is None or dt >= cutoff:
                kept.append(r)
        rows = kept
    year = spec.get("year")
    if year and ds.date_column:
        rows = [r for r in rows if _year(r.get(ds.date_column)) == int(year)]
    contains = spec.get("contains")
    field = spec.get("field")
    if contains:
        needle = str(contains).lower()
        if field and field in ds.columns:
            rows = [r for r in rows if needle in str(r.get(field, "")).lower()]
        else:
            rows = [
                r for r in rows
                if any(needle in str(v).lower() for v in r.values())
            ]
    preview = json.dumps(rows[:15], default=str)
    return Dataset(
        filename=ds.filename,
        columns=ds.columns,
        rows=rows,
        numeric_columns=ds.numeric_columns,
        date_column=ds.date_column,
        text_preview=preview,
    )


def compare_columns(ds: Dataset, col_a: str, col_b: str) -> dict[str, Any]:
    a_vals = [float(r[col_a]) for r in ds.rows if _is_number(r.get(col_a))]
    b_vals = [float(r[col_b]) for r in ds.rows if _is_number(r.get(col_b))]
    avg_a = sum(a_vals) / len(a_vals) if a_vals else 0.0
    avg_b = sum(b_vals) / len(b_vals) if b_vals else 0.0
    delta = avg_a - avg_b
    pct = (delta / avg_b * 100.0) if avg_b else None
    return {
        "left": {"column": col_a, "mean": avg_a, "n": len(a_vals)},
        "right": {"column": col_b, "mean": avg_b, "n": len(b_vals)},
        "delta": delta,
        "pct_delta": pct,
    }


def compare_elements(elements: list[dict[str, Any]], id_a: str, id_b: str) -> dict[str, Any]:
    a = next((e for e in elements if e["id"] == id_a), None) or {}
    b = next((e for e in elements if e["id"] == id_b), None) or {}
    na = _parse_numeric_label(a.get("value"))
    nb = _parse_numeric_label(b.get("value"))
    delta = None
    pct = None
    if na is not None and nb is not None:
        delta = na - nb
        pct = (delta / nb * 100.0) if nb else None
    return {
        "left": {"id": id_a, "label": a.get("label", id_a), "value": a.get("value"), "numeric": na},
        "right": {"id": id_b, "label": b.get("label", id_b), "value": b.get("value"), "numeric": nb},
        "delta": delta,
        "pct_delta": pct,
    }


def dataset_summary(ds: Dataset, max_rows: int = 40) -> str:
    buf = [f"File: {ds.filename}", f"Columns: {', '.join(ds.columns)}", f"Rows: {len(ds.rows)}"]
    buf.append(json.dumps(ds.rows[:max_rows], default=str)[:12000])
    return "\n".join(buf)


def _from_csv(filename: str, text: str, delim: str) -> Dataset:
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    columns = list(reader.fieldnames or [])
    rows = []
    for i, row in enumerate(reader):
        if i >= 2000:
            break
        rows.append(dict(row))
    return _finalize(filename, columns, rows, text[:8000])


def _from_json(filename: str, text: str) -> Dataset:
    data = json.loads(text)
    if isinstance(data, dict):
        for key in ("rows", "data", "records", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list) or not data:
        return Dataset(filename, [], [], [], None, text[:8000])
    columns = list(data[0].keys()) if isinstance(data[0], dict) else ["value"]
    rows = data[:2000] if isinstance(data[0], dict) else [{"value": v} for v in data[:2000]]
    return _finalize(filename, columns, rows, text[:8000])


def _finalize(filename: str, columns: list[str], rows: list[dict], preview: str) -> Dataset:
    numeric = []
    date_col = None
    for col in columns:
        vals = [r.get(col) for r in rows[:50]]
        nums = sum(1 for v in vals if _is_number(v))
        dates = sum(1 for v in vals if _parse_date(v) is not None)
        if nums >= max(3, len(vals) * 0.6):
            numeric.append(col)
        if date_col is None and dates >= max(3, len(vals) * 0.5):
            date_col = col
        if date_col is None and re.search(r"date|time|day", col, re.I):
            date_col = col
    return Dataset(filename, columns, rows, numeric, date_col, preview)


def _is_number(v: Any) -> bool:
    if v is None or v == "":
        return False
    try:
        float(str(v).replace(",", "").replace("$", "").replace("%", ""))
        return True
    except ValueError:
        return False


def _parse_numeric_label(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    if s.upper().endswith("M"):
        mult = 1_000_000
        s = s[:-1]
    elif s.upper().endswith("K"):
        mult = 1_000
        s = s[:-1]
    s = s.replace("$", "")
    try:
        return float(s) * mult
    except ValueError:
        return None


def _parse_date(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()[:32]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _year(v: Any) -> int | None:
    dt = _parse_date(v)
    return dt.year if dt else None


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "col"


def _fmt(n: float) -> str:
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"{n:,.1f}"
    if abs(n) < 1:
        return f"{n:.3f}"
    return f"{n:.2f}"

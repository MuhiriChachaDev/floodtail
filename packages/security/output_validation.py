"""Validate LLM text against a frozen numeric allowlist (no invented KES)."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

# Money-ish tokens: plain integers/decimals, optionally with commas / KES prefix/suffix
_MONEY_RE = re.compile(
    r"(?i)(?:kes\s*)?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{4,})"
)


def flatten_allowlist_numbers(allowlist: dict[str, Any]) -> set[float]:
    """Collect numeric values (and rounded ints) the LLM may cite."""
    out: set[float] = set()
    for v in allowlist.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out.add(float(v))
            out.add(float(round(v)))
            out.add(float(int(round(v))))
        elif isinstance(v, dict):
            out |= flatten_allowlist_numbers(v)
        elif isinstance(v, (list, tuple)):
            for item in v:
                if isinstance(item, (int, float)):
                    out.add(float(item))
                elif isinstance(item, dict):
                    out |= flatten_allowlist_numbers(item)
    return out


def extract_money_tokens(text: str) -> list[float]:
    """Pull candidate money figures from prose (skips tiny ints like 1–3 in bullets)."""
    found: list[float] = []
    for m in _MONEY_RE.finditer(text or ""):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        # Skip small integers that are likely counts in "1–3 next steps" style text
        if val.is_integer() and abs(val) < 1000:
            continue
        found.append(val)
    return found


def numbers_in_allowlist(
    text: str,
    allowlist: dict[str, Any],
    *,
    rtol: float = 1e-4,
    atol: float = 1.0,
) -> tuple[bool, list[float]]:
    """
    Return (ok, invented) where invented are money tokens not matching allowlist.

    Matching: exact float equality within atol/rtol, or rounded to nearest integer
    when the allowlist contains that integer (LLM may format without decimals).
    """
    allowed = flatten_allowlist_numbers(allowlist)
    invented: list[float] = []
    for token in extract_money_tokens(text):
        if _matches_any(token, allowed, rtol=rtol, atol=atol):
            continue
        invented.append(token)
    return (len(invented) == 0, invented)


def _matches_any(token: float, allowed: Iterable[float], *, rtol: float, atol: float) -> bool:
    for a in allowed:
        if abs(token - a) <= max(atol, rtol * abs(a)):
            return True
        # LLM often writes floor as integer KES
        if abs(round(token) - round(a)) < 1e-6 and abs(token - a) < max(1.0, 0.01 * abs(a)):
            return True
    return False


def validate_insight_fields(
    *,
    narrative: str,
    why: list[str],
    next_steps: list[str],
    allowlist: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate all textual insight fields against allowlist."""
    blobs = [narrative, *why, *next_steps]
    errors: list[str] = []
    for blob in blobs:
        ok, invented = numbers_in_allowlist(blob, allowlist)
        if not ok:
            errors.append(f"invented numbers not in allowlist: {invented}")
    return (len(errors) == 0, errors)


def reject_invented_kes(
    text: str,
    allowlist: dict[str, Any],
) -> Optional[str]:
    """Return error message if text invents KES figures, else None."""
    ok, invented = numbers_in_allowlist(text, allowlist)
    if ok:
        return None
    return f"Invented money figures rejected: {invented}"

"""FLOODTAIL — Numeric Grounding Guard & Truthfulness Enforcement.

Provides an immutable verification registry for all numeric outputs produced by
the 11 catastrophe intelligence agents during a model execution run.
Prevents hallucinated or ungrounded figures from entering human underwriting dialogues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.exceptions import ValidationError
from src.logging_config import get_logger

logger = get_logger("grounding")


@dataclass
class GroundingEntry:
    """Immutable record of an authentic quantitative model output."""

    run_id: str
    field_name: str
    value: float
    source_agent: str
    metric_category: str
    unit: str = "KES"
    tolerance: float = 0.01  # 1% relative tolerance
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GroundingGuard:
    """Trust infrastructure that verifies numbers against current tool outputs."""

    def __init__(self) -> None:
        self._registry: dict[str, list[GroundingEntry]] = {}

    def register_output(
        self,
        run_id: str,
        field_name: str,
        value: float,
        source_agent: str,
        metric_category: str = "GENERAL",
        unit: str = "KES",
        tolerance: float = 0.01,
    ) -> GroundingEntry:
        """Register a verified numeric output from an engine or agent."""
        entry = GroundingEntry(
            run_id=run_id,
            field_name=field_name,
            value=float(value),
            source_agent=source_agent,
            metric_category=metric_category,
            unit=unit,
            tolerance=tolerance,
        )
        if run_id not in self._registry:
            self._registry[run_id] = []
        self._registry[run_id].append(entry)
        return entry

    def get_run_entries(self, run_id: str) -> list[GroundingEntry]:
        """Retrieve all registered outputs for a given run."""
        return self._registry.get(run_id, [])

    def verify_numeric_claim(
        self,
        run_id: str,
        claimed_value: float,
        field_name: Optional[str] = None,
        tolerance: Optional[float] = None,
    ) -> tuple[bool, Optional[GroundingEntry]]:
        """Verify whether a specific numeric value matches a registered output."""
        entries = self._registry.get(run_id, [])
        for entry in entries:
            if field_name and entry.field_name.lower() != field_name.lower():
                continue
            tol = tolerance if tolerance is not None else entry.tolerance
            if abs(entry.value) > 1e-6:
                rel_diff = abs(claimed_value - entry.value) / abs(entry.value)
                if rel_diff <= tol:
                    return True, entry
            else:
                if abs(claimed_value - entry.value) <= 1e-4:
                    return True, entry
        return False, None

    def audit_dialogue_claim(
        self,
        run_id: str,
        claim_text: str,
    ) -> dict[str, Any]:
        """Inspects dialogue text and identifies whether cited numbers are grounded."""
        entries = self._registry.get(run_id, [])
        # Extract explicit currency or formatted large numbers (e.g. KES 372,400,000 or 1,234,567.89)
        pattern = r"(?:KES\s*|\$)?([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?)"
        matches = re.findall(pattern, claim_text)
        
        extracted_numbers: list[float] = []
        for m in matches:
            clean = m.replace(",", "")
            try:
                val = float(clean)
                if val > 0:
                    extracted_numbers.append(val)
            except ValueError:
                continue

        verified_count = 0
        unverified_numbers: list[float] = []

        for num in extracted_numbers:
            is_valid, _ = self.verify_numeric_claim(run_id, num, tolerance=0.05)
            if is_valid:
                verified_count += 1
            else:
                unverified_numbers.append(num)

        is_grounded = len(unverified_numbers) == 0 and len(extracted_numbers) > 0

        return {
            "is_grounded": is_grounded,
            "total_numbers_found": len(extracted_numbers),
            "verified_count": verified_count,
            "unverified_numbers": unverified_numbers,
            "registered_entries_count": len(entries),
        }

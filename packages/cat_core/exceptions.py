"""CAT core errors."""

from __future__ import annotations


class CatCoreError(Exception):
    """Base CAT core error."""


class ExposureDQError(CatCoreError):
    """Fatal data-quality breach on ingest."""


class ReconciliationError(CatCoreError):
    """Financial totals failed to reconcile."""

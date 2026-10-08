"""FLOODTAIL — Reinsurance Treaty Layering & Excess of Loss (XOL) Engine.

Structures cedant portfolio risk into Excess of Loss (XOL) layers:
1. Cedant Retention
2. Layer 1 (Working Cat Layer: Attachment -> Limit)
3. Layer 2 (Upper Tail Cat Layer: Attachment -> Limit)
4. Cedant Net Retained & Exhaustion Loss
Computes Layer AAL, Layer TVaR, Indicated Layer Premium, and Rate-on-Line (ROL).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.exceptions import ModelCalculationError
from src.logging_config import get_logger

logger = get_logger("treaty")


@dataclass
class LayerDefinition:
    """Configurable definition of a reinsurance Excess of Loss layer."""

    layer_name: str
    attachment_point: float
    limit: float
    ceded_share_pct: float = 100.0


@dataclass
class ReinsuranceLayerResult:
    """Calculated financial metrics for a single reinsurance layer."""

    layer_name: str
    attachment_point: float
    limit: float
    ceded_share_pct: float
    layer_aal: float
    layer_var_996: float
    layer_tvar_996: float
    indicated_layer_premium: float
    rate_on_line_pct: float
    exhaustion_probability_pct: float


@dataclass
class TreatyStructureResult:
    """Comprehensive portfolio treaty structure evaluation."""

    total_gross_aal: float
    total_gross_tvar_996: float
    cedant_retained_aal: float
    cedant_retained_tvar_996: float
    total_ceded_layer_aal: float
    total_ceded_layer_premium: float
    layers: list[ReinsuranceLayerResult]
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TreatyEngine:
    """Evaluates reinsurance excess of loss structures from simulated annual loss distributions."""

    def __init__(self, cost_of_capital_rate: float = 0.10, expense_rate: float = 0.08) -> None:
        self.coc_rate = cost_of_capital_rate
        self.exp_rate = expense_rate

    def evaluate_treaty(
        self,
        ylt_df: pd.DataFrame,
        layers: Optional[list[LayerDefinition]] = None,
    ) -> TreatyStructureResult:
        """Slices the YLT annual loss distribution across reinsurance treaty layers."""
        if ylt_df is None or ylt_df.empty:
            raise ModelCalculationError("YLT DataFrame is empty for treaty analysis.")

        col = "annual_loss" if "annual_loss" in ylt_df.columns else "loss"
        losses = ylt_df[col].to_numpy(dtype=float)
        n_years = len(losses)

        # Default canonical 2-layer reinsurance structure for demo if not supplied
        if not layers:
            gross_pml_250 = float(np.percentile(losses, 99.6))
            att1 = gross_pml_250 * 0.15
            lim1 = gross_pml_250 * 0.35
            att2 = att1 + lim1
            lim2 = gross_pml_250 * 0.50

            layers = [
                LayerDefinition(
                    layer_name="Cat XOL Layer 1 (Working Layer)",
                    attachment_point=att1,
                    limit=lim1,
                    ceded_share_pct=100.0,
                ),
                LayerDefinition(
                    layer_name="Cat XOL Layer 2 (Tail Protection)",
                    attachment_point=att2,
                    limit=lim2,
                    ceded_share_pct=100.0,
                ),
            ]

        # Gross metrics
        gross_aal = float(np.mean(losses))
        gross_var_996 = float(np.percentile(losses, 99.6))
        gross_tail = losses[losses >= gross_var_996]
        gross_tvar_996 = float(np.mean(gross_tail)) if len(gross_tail) > 0 else gross_var_996

        layer_results: list[ReinsuranceLayerResult] = []
        total_ceded_losses = np.zeros(n_years, dtype=float)

        for layer in layers:
            att = layer.attachment_point
            lim = layer.limit
            share = layer.ceded_share_pct / 100.0

            # Layer loss for each year: min(max(loss - attachment, 0), limit) * share
            raw_layer_loss = np.minimum(np.maximum(losses - att, 0.0), lim) * share
            total_ceded_losses += raw_layer_loss

            layer_aal = float(np.mean(raw_layer_loss))
            layer_var = float(np.percentile(raw_layer_loss, 99.6))
            layer_tail = raw_layer_loss[raw_layer_loss >= layer_var]
            layer_tvar = float(np.mean(layer_tail)) if len(layer_tail) > 0 else layer_var

            net_tail = max(0.0, layer_tvar - layer_aal)
            tail_chg = self.coc_rate * net_tail
            exp_load = self.exp_rate * (layer_aal + tail_chg)
            premium = layer_aal + tail_chg + exp_load

            rol = (premium / lim * 100.0) if lim > 0 else 0.0
            exhaust_prob = float(np.mean(raw_layer_loss >= (lim * share * 0.99)) * 100.0)

            layer_results.append(
                ReinsuranceLayerResult(
                    layer_name=layer.layer_name,
                    attachment_point=att,
                    limit=lim,
                    ceded_share_pct=layer.ceded_share_pct,
                    layer_aal=layer_aal,
                    layer_var_996=layer_var,
                    layer_tvar_996=layer_tvar,
                    indicated_layer_premium=premium,
                    rate_on_line_pct=round(rol, 2),
                    exhaustion_probability_pct=round(exhaust_prob, 3),
                )
            )

        # Cedant retained losses
        retained_losses = np.maximum(0.0, losses - total_ceded_losses)
        ret_aal = float(np.mean(retained_losses))
        ret_var = float(np.percentile(retained_losses, 99.6))
        ret_tail = retained_losses[retained_losses >= ret_var]
        ret_tvar = float(np.mean(ret_tail)) if len(ret_tail) > 0 else ret_var

        total_ceded_aal = sum(lr.layer_aal for lr in layer_results)
        total_ceded_prem = sum(lr.indicated_layer_premium for lr in layer_results)

        return TreatyStructureResult(
            total_gross_aal=gross_aal,
            total_gross_tvar_996=gross_tvar_996,
            cedant_retained_aal=ret_aal,
            cedant_retained_tvar_996=ret_tvar,
            total_ceded_layer_aal=total_ceded_aal,
            total_ceded_layer_premium=total_ceded_prem,
            layers=layer_results,
        )

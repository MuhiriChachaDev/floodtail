"""Tests for FLOODTAIL Shadow Exposure and Protection Gap Engine."""

import pandas as pd
import pytest

from src.exceptions import ModelCalculationError
from src.shadow_exposure import ShadowExposureEngine


def test_shadow_exposure_calculation():
    """Validates shadow exposure multiplier and protection gap calculations."""
    engine = ShadowExposureEngine()
    
    portfolio_df = pd.DataFrame({
        "policy_id": ["POL-01", "POL-02", "POL-03"],
        "region": ["Nairobi", "Mombasa", "Kisumu"],
        "insured_value": [100_000_000.0, 50_000_000.0, 20_000_000.0],
    })
    
    shadow_df, summary = engine.evaluate_portfolio_shadow(portfolio_df)
    
    assert len(shadow_df) == 3
    assert "shadow_tiv_estimate" in shadow_df.columns
    assert summary["total_insured_tiv"] == 170_000_000.0
    assert summary["total_shadow_tiv_estimate"] > summary["total_insured_tiv"]
    assert summary["aggregate_protection_gap_pct"] > 50.0
    assert summary["high_amplification_policy_count"] == 2


def test_shadow_exposure_empty():
    """Verifies that empty DataFrame raises ModelCalculationError."""
    engine = ShadowExposureEngine()
    with pytest.raises(ModelCalculationError):
        engine.evaluate_portfolio_shadow(pd.DataFrame())

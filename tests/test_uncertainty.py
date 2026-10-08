"""Tests for FLOODTAIL Uncertainty Corridors and Confidence Engine."""

import numpy as np
import pandas as pd
import pytest

from src.exceptions import ModelCalculationError
from src.uncertainty import UncertaintyEngine, UncertaintyMetric, PremiumCorridor


def test_uncertainty_engine_aal_bootstrap():
    """Validates bootstrap confidence interval calculation for AAL."""
    engine = UncertaintyEngine(n_bootstraps=200, seed=42)
    
    # 1,000 years of synthetic loss data
    rng = np.random.default_rng(42)
    losses = rng.exponential(scale=10000.0, size=1000)
    ylt_df = pd.DataFrame({"year": range(1, 1001), "loss": losses})
    
    aal_unc = engine.compute_aal_uncertainty(ylt_df)
    
    assert isinstance(aal_unc, UncertaintyMetric)
    assert aal_unc.metric_name == "Average Annual Loss (AAL)"
    assert aal_unc.point_estimate == pytest.approx(np.mean(losses), rel=1e-4)
    assert aal_unc.lower_80 < aal_unc.point_estimate < aal_unc.upper_80
    assert aal_unc.lower_90 <= aal_unc.lower_80
    assert aal_unc.upper_90 >= aal_unc.upper_80
    assert aal_unc.relative_uncertainty_pct > 0
    assert len(aal_unc.primary_drivers) > 0


def test_uncertainty_engine_tvar_bootstrap():
    """Validates TVaR 99.6% confidence interval calculation."""
    engine = UncertaintyEngine(n_bootstraps=200, seed=42)
    rng = np.random.default_rng(42)
    losses = rng.lognormal(mean=8.0, sigma=1.2, size=1000)
    ylt_df = pd.DataFrame({"year": range(1, 1001), "loss": losses})
    
    tvar_unc = engine.compute_tvar_uncertainty(ylt_df, confidence_level=0.99)
    
    assert isinstance(tvar_unc, UncertaintyMetric)
    assert tvar_unc.lower_80 < tvar_unc.upper_80
    assert tvar_unc.point_estimate > np.mean(losses)


def test_uncertainty_engine_premium_corridor():
    """Validates Low, Base, High indicated technical premium confidence corridor."""
    engine = UncertaintyEngine(n_bootstraps=200, seed=42)
    rng = np.random.default_rng(42)
    losses = rng.exponential(scale=50000.0, size=1000)
    ylt_df = pd.DataFrame({"year": range(1, 1001), "loss": losses})
    
    point_aal = float(np.mean(losses))
    point_tvar = float(np.percentile(losses, 99.6)) * 1.5
    base_premium = point_aal + 0.10 * (point_tvar - point_aal) + 0.10 * (point_aal + 0.10 * (point_tvar - point_aal))
    
    corridor = engine.compute_premium_corridor(
        ylt_df=ylt_df,
        point_technical_premium=base_premium,
        point_aal=point_aal,
        point_tvar=point_tvar,
        coc_rate=0.10,
        exp_rate=0.10,
    )
    
    assert isinstance(corridor, PremiumCorridor)
    assert corridor.low_premium < corridor.base_premium < corridor.high_premium
    assert corridor.uncertainty_span_pct > 0
    assert len(corridor.primary_drivers) > 0


def test_uncertainty_engine_empty_input():
    """Verifies that empty YLT raises ModelCalculationError."""
    engine = UncertaintyEngine()
    empty_df = pd.DataFrame()
    
    with pytest.raises(ModelCalculationError):
        engine.compute_aal_uncertainty(empty_df)

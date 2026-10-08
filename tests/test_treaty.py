"""Tests for FLOODTAIL Reinsurance Treaty Layering Engine."""

import numpy as np
import pandas as pd
import pytest

from src.exceptions import ModelCalculationError
from src.treaty import LayerDefinition, TreatyEngine, TreatyStructureResult


def test_treaty_engine_evaluation():
    """Validates reinsurance layer slicing, layer AAL/TVaR, and premium calculations."""
    engine = TreatyEngine(cost_of_capital_rate=0.10, expense_rate=0.08)
    
    rng = np.random.default_rng(42)
    losses = rng.exponential(scale=50_000.0, size=1000)
    ylt_df = pd.DataFrame({"annual_loss": losses})
    
    layers = [
        LayerDefinition(
            layer_name="Layer 1",
            attachment_point=50_000.0,
            limit=100_000.0,
            ceded_share_pct=100.0,
        ),
    ]
    
    result = engine.evaluate_treaty(ylt_df, layers=layers)
    
    assert isinstance(result, TreatyStructureResult)
    assert result.total_gross_aal > result.cedant_retained_aal
    assert len(result.layers) == 1
    assert result.layers[0].layer_aal > 0
    assert result.layers[0].indicated_layer_premium > 0
    assert result.layers[0].rate_on_line_pct > 0


def test_treaty_engine_default_layers():
    """Validates automatic creation of default 2-layer structure."""
    engine = TreatyEngine()
    rng = np.random.default_rng(42)
    losses = rng.exponential(scale=100_000.0, size=1000)
    ylt_df = pd.DataFrame({"annual_loss": losses})
    
    result = engine.evaluate_treaty(ylt_df)
    assert len(result.layers) == 2
    assert result.layers[0].attachment_point < result.layers[1].attachment_point


def test_treaty_engine_empty_input():
    """Verifies that empty YLT raises ModelCalculationError."""
    engine = TreatyEngine()
    with pytest.raises(ModelCalculationError):
        engine.evaluate_treaty(pd.DataFrame())

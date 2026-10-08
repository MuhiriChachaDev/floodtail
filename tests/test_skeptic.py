"""Tests for FLOODTAIL Skeptic Agent and Adversarial Sensitivity Module."""

import numpy as np
import pandas as pd
import pytest

from src.exceptions import ModelCalculationError
from src.skeptic import SkepticAgent, SkepticReport, SkepticScenarioResult


def test_skeptic_agent_evaluation():
    """Validates Base, Low, and High scenario computation and sensitivity ranking."""
    agent = SkepticAgent(cost_of_capital_rate=0.10, expense_rate=0.10)
    
    portfolio_df = pd.DataFrame({
        "policy_id": ["POL-01", "POL-02"],
        "insured_value": [1000000.0, 2000000.0],
        "region": ["Nairobi", "Mombasa"],
    })
    
    rng = np.random.default_rng(42)
    losses = rng.exponential(scale=20000.0, size=1000)
    ylt_df = pd.DataFrame({"simulation_year": range(1, 1001), "annual_loss": losses})
    
    report = agent.evaluate_scenarios(
        portfolio_df=portfolio_df,
        ylt_df=ylt_df,
        base_technical_premium=35000.0,
    )
    
    assert isinstance(report, SkepticReport)
    assert report.low_case.portfolio_aal < report.base_case.portfolio_aal < report.high_case.portfolio_aal
    assert report.low_case.portfolio_tvar_996 < report.base_case.portfolio_tvar_996 < report.high_case.portfolio_tvar_996
    assert report.low_case.indicated_premium < report.base_case.indicated_premium < report.high_case.indicated_premium
    assert len(report.sensitivities) == 3
    assert "Nairobi" in report.most_influential_assumption
    assert len(report.challenge_narrative) > 0


def test_skeptic_agent_empty_inputs():
    """Verifies that empty DataFrames raise ModelCalculationError."""
    agent = SkepticAgent()
    empty_df = pd.DataFrame()
    valid_df = pd.DataFrame({"policy_id": ["POL-01"], "insured_value": [100.0]})
    
    with pytest.raises(ModelCalculationError):
        agent.evaluate_scenarios(empty_df, valid_df, 10.0)
        
    with pytest.raises(ModelCalculationError):
        agent.evaluate_scenarios(valid_df, empty_df, 10.0)

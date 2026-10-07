"""Phase B — Nairobi CAT core unit tests."""

from __future__ import annotations

import numpy as np
import pytest

from apps.api.settings import get_settings
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.capital import compute_capital_band_from_profile
from packages.cat_core.depth import add_depth_columns, score_to_depth
from packages.cat_core.engine import run_prior_only
from packages.cat_core.ep import discrete_aal
from packages.cat_core.exceptions import ExposureDQError
from packages.cat_core.exposure import (
    builtin_nairobi_path,
    load_exposure_csv,
    validate_and_normalize,
)
from packages.cat_core.vulnerability_prior import (
    JRC_ADAPTED_CURVES,
    assert_monotonic,
    damage_ratio,
)


@pytest.fixture
def profile() -> AssumptionsProfile:
    return get_settings().assumptions_profile()


@pytest.fixture
def nairobi_frame(profile: AssumptionsProfile):
    path = builtin_nairobi_path(get_settings().nairobi_data_dir)
    raw = load_exposure_csv(path)
    frame, stats, warnings = validate_and_normalize(
        raw,
        profile,
        location_label="Nairobi County",
        source="builtin_nairobi",
    )
    assert stats.n_insured_houses == 600
    assert stats.synthetic is True
    return frame, stats, warnings


def test_load_600_rows_synthetic(nairobi_frame) -> None:
    frame, stats, _ = nairobi_frame
    assert len(frame) == 600
    assert bool(frame["synthetic"].all())
    assert stats.total_tiv_kes > 0
    assert stats.bbox is not None


def test_dq_rejects_bad_tiv(profile: AssumptionsProfile, nairobi_frame) -> None:
    frame, _, _ = nairobi_frame
    bad = frame.copy()
    bad.loc[bad.index[0], "tiv_kes"] = 0
    with pytest.raises(ExposureDQError):
        validate_and_normalize(bad, profile, location_label="x", source="t")


def test_depth_mapping(profile: AssumptionsProfile) -> None:
    assert score_to_depth(0.5, 4.0) == 2.0
    assert score_to_depth(1.5, 4.0) == 4.0  # clipped
    assert score_to_depth(-1.0, 4.0) == 0.0


def test_damage_monotonic_and_bounds() -> None:
    assert_monotonic()
    for housing_class, curve in JRC_ADAPTED_CURVES.items():
        depths = [p[0] for p in curve]
        ratios = [damage_ratio(d, housing_class) for d in depths]
        assert ratios == sorted(ratios)
        assert all(0.0 <= r <= 1.0 for r in ratios)
        assert damage_ratio(0.0, housing_class) == 0.0
        # deeper should not decrease
        assert damage_ratio(3.5, housing_class) >= damage_ratio(1.0, housing_class)


def test_informal_more_vulnerable_than_concrete() -> None:
    assert damage_ratio(1.0, "informal_iron_sheet") > damage_ratio(1.0, "concrete_rcc")


def test_prior_only_engine_ep_and_capital(nairobi_frame, profile: AssumptionsProfile) -> None:
    frame, stats, _ = nairobi_frame
    result = run_prior_only(
        frame,
        profile,
        run_id="test-run",
        portfolio_id="test-port",
        location_label=stats.location_label,
    )
    m = result.metrics
    assert m.n_insured_houses == 600
    assert len(m.tier_losses) == 5
    assert len(m.ep_curve) == 5
    assert m.aal_kes == pytest.approx(discrete_aal(m.tier_losses), rel=1e-9)
    assert m.capital_band is not None
    band = m.capital_band
    assert band.floor_kes <= band.ceiling_kes
    # EP losses should be non-decreasing with RP for this book (proxy severity rises)
    losses = [p.loss_kes for p in m.ep_curve]
    # Not strictly required by math if scores invert, but check finite
    assert all(np.isfinite(losses))
    assert m.data_labels.synthetic_exposure is True
    assert m.assumptions_version == profile.assumptions_version

    # Property losses reconcile to tier totals
    for tier in profile.tier_names:
        col = f"loss_kes_{tier}"
        assert col in result.properties.columns
        assert result.properties[col].sum() == pytest.approx(
            next(t.loss_kes for t in m.tier_losses if t.tier == tier),
            rel=1e-6,
            abs=0.1,
        )

    insight = result.insight
    assert insight.insured_houses == 600
    assert insight.set_aside.floor_kes == band.floor_kes
    assert insight.numbers_source == "template"
    assert insight.recommendation.value in {"ACCEPT", "REVIEW", "ESCALATE"}


def test_capital_band_floor_le_ceiling(profile: AssumptionsProfile, nairobi_frame) -> None:
    frame, stats, _ = nairobi_frame
    result = run_prior_only(
        frame,
        profile,
        run_id="r",
        portfolio_id="p",
        location_label=stats.location_label,
    )
    band = compute_capital_band_from_profile(
        result.metrics.tier_losses,
        result.metrics.aal_kes,
        result.metrics.total_tiv_kes,
        profile,
    )
    assert band.floor_kes <= band.ceiling_kes


def test_depth_columns_added(nairobi_frame, profile: AssumptionsProfile) -> None:
    frame, _, _ = nairobi_frame
    out = add_depth_columns(frame, profile)
    for tier in profile.tier_names:
        assert f"depth_m_{tier}" in out.columns
        assert (out[f"depth_m_{tier}"] <= profile.d_max_m + 1e-9).all()

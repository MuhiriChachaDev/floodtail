"""Prototype XL layering + technical premium unit tests."""

from __future__ import annotations

import pytest

from apps.api.settings import get_settings
from packages.cat_core.assumptions import PricingPolicy, TreatyPolicy
from packages.cat_core.engine import run_prior_only
from packages.cat_core.ep import build_tier_losses
from packages.cat_core.exposure import (
    builtin_nairobi_path,
    load_exposure_csv,
    validate_and_normalize,
)
from packages.cat_core.pricing import technical_premium
from packages.cat_core.reinsurance import apply_xl, build_financial_view, resolve_treaty_terms
from packages.cat_core.types import TreatyTerms


@pytest.fixture
def profile():
    return get_settings().assumptions_profile()


@pytest.fixture
def nairobi_frame(profile):
    path = builtin_nairobi_path(get_settings().nairobi_data_dir)
    raw = load_exposure_csv(path)
    frame, stats, _ = validate_and_normalize(
        raw, profile, location_label="Nairobi County", source="builtin_nairobi"
    )
    return frame, stats


def test_apply_xl_below_attachment() -> None:
    treaty = TreatyTerms(
        attachment_kes=100.0, limit_kes=50.0, retention_kes=100.0
    )
    retained, recovery, net = apply_xl(80.0, treaty)
    assert retained == 80.0
    assert recovery == 0.0
    assert net == 80.0


def test_apply_xl_within_layer() -> None:
    treaty = TreatyTerms(
        attachment_kes=100.0, limit_kes=50.0, retention_kes=100.0
    )
    retained, recovery, net = apply_xl(130.0, treaty)
    assert retained == 100.0
    assert recovery == 30.0
    assert net == 100.0


def test_apply_xl_exhausts_limit() -> None:
    treaty = TreatyTerms(
        attachment_kes=100.0, limit_kes=50.0, retention_kes=100.0
    )
    retained, recovery, net = apply_xl(200.0, treaty)
    assert retained == 100.0
    assert recovery == 50.0
    assert net == 150.0


def test_resolve_treaty_from_tiv_fractions() -> None:
    policy = TreatyPolicy(attachment_tiv_fraction=0.05, limit_tiv_fraction=0.15)
    terms = resolve_treaty_terms(policy, total_tiv_kes=1_000_000.0)
    assert terms.attachment_kes == pytest.approx(50_000.0)
    assert terms.limit_kes == pytest.approx(150_000.0)
    assert terms.retention_kes == terms.attachment_kes
    assert terms.status == "PROTOTYPE"


def test_technical_premium_load() -> None:
    indication = technical_premium(1_000.0, PricingPolicy(default_load_factor=1.25))
    assert indication.technical_premium_kes == pytest.approx(1_250.0)
    assert indication.status == "PROTOTYPE"
    assert "human approval" in " ".join(indication.notes).lower()


def test_engine_emits_financial_and_pricing(nairobi_frame, profile) -> None:
    frame, stats = nairobi_frame
    result = run_prior_only(
        frame,
        profile,
        run_id="fin-test",
        portfolio_id="p",
        location_label=stats.location_label,
    )
    m = result.metrics
    assert m.financial is not None
    assert m.pricing is not None
    assert m.financial.aal_gross_kes == pytest.approx(m.aal_kes, rel=1e-9)
    assert m.financial.aal_net_kes <= m.financial.aal_gross_kes + 1e-6
    assert m.financial.aal_ceded_kes == pytest.approx(
        m.financial.aal_gross_kes - m.financial.aal_net_kes, abs=0.02
    )
    assert len(m.financial.ep_curve_net) == len(m.ep_curve)
    assert m.pricing.technical_premium_kes == pytest.approx(
        m.aal_kes * m.pricing.load_factor, rel=1e-9
    )
    # Net never exceeds gross per tier
    for layer in m.financial.layered_by_tier:
        assert layer.net_kes <= layer.gross_kes + 1e-6
        assert layer.recovery_kes >= -1e-6


def test_financial_view_with_absolute_override(profile) -> None:
    tiers = build_tier_losses(
        {
            "common": 10.0,
            "occasional": 40.0,
            "moderate": 80.0,
            "severe": 150.0,
            "extreme": 300.0,
        },
        profile,
    )
    policy = TreatyPolicy(attachment_kes=100.0, limit_kes=100.0)
    view = build_financial_view(tiers, policy, total_tiv_kes=1_000_000.0)
    severe = next(t for t in view.layered_by_tier if t.tier == "severe")
    assert severe.recovery_kes == pytest.approx(50.0)
    assert severe.net_kes == pytest.approx(100.0)
    extreme = next(t for t in view.layered_by_tier if t.tier == "extreme")
    assert extreme.recovery_kes == pytest.approx(100.0)
    assert extreme.net_kes == pytest.approx(200.0)

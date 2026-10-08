"""Portfolio geography must not inherit Nairobi layers by default."""

from __future__ import annotations

import pandas as pd

from packages.cat_core.geo_scope import (
    bbox_overlaps,
    frame_bbox,
    hotspots_near_portfolio,
)


def test_bbox_overlaps_adjacent():
    a = (-0.2, 34.7, 0.0, 34.9)  # Kisumu-ish
    b = (-1.4, 36.6, -1.1, 37.1)  # Nairobi-ish
    assert not bbox_overlaps(a, b, pad_deg=0.05)
    assert bbox_overlaps(a, a, pad_deg=0.0)


def test_hotspots_near_portfolio_filters_cross_city():
    portfolio = pd.DataFrame(
        {
            "lat": [-0.09, -0.10],
            "lon": [34.76, 34.75],
        }
    )
    hotspots = pd.DataFrame(
        {
            "name": ["Kibera", "Kisumu CBD"],
            "lat": [-1.31, -0.091],
            "lon": [36.79, 34.768],
        }
    )
    near = hotspots_near_portfolio(hotspots, portfolio, pad_deg=0.45)
    assert near is not None
    assert list(near["name"]) == ["Kisumu CBD"]


def test_hotspots_none_when_far():
    portfolio = pd.DataFrame({"lat": [-0.09], "lon": [34.76]})
    hotspots = pd.DataFrame(
        {"name": ["Kibera"], "lat": [-1.31], "lon": [36.79]}
    )
    assert hotspots_near_portfolio(hotspots, portfolio, pad_deg=0.2) is None


def test_frame_bbox():
    df = pd.DataFrame({"lat": [1.0, 2.0], "lon": [3.0, 4.0]})
    assert frame_bbox(df) == (1.0, 3.0, 2.0, 4.0)

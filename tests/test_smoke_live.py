"""Live network test proving the Google consent-wall bypass still works.

Skipped by default (`pytest -q`). Run explicitly with `pytest -q -m live`.
"""

import datetime as dt

import pytest

from googleflights_mcp.flights import search

pytestmark = pytest.mark.live


def test_ist_to_ayt_returns_priced_results():
    departure = (dt.date.today() + dt.timedelta(days=14)).isoformat()

    out = search(
        from_airport="IST",
        to_airport="AYT",
        departure_date=departure,
        trip="one-way",
        seat="economy",
        currency="TRY",
        max_results=5,
    )

    assert "error" not in out, out.get("error")
    assert out["count"] > 0
    assert isinstance(out["cheapest_price"], (int, float))
    prices = [r["price"] for r in out["results"]]
    assert prices == sorted(prices)

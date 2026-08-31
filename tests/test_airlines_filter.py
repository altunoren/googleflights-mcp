"""Network-free tests for the `airlines` filter on search()."""

from fast_flights.parser import JsMetadata, ResultList

import googleflights_mcp.flights as flights_mod
from googleflights_mcp.flights import search


def _stub_fetch_and_parse(monkeypatch, capture: dict):
    def fake_fetch_and_parse(query):
        capture["query"] = query
        result = ResultList([])
        result.metadata = JsMetadata(airlines=[], alliances=[])
        return result

    monkeypatch.setattr(flights_mod, "fetch_and_parse", fake_fetch_and_parse)


def test_airlines_filter_reaches_the_query(monkeypatch):
    capture: dict = {}
    _stub_fetch_and_parse(monkeypatch, capture)

    out = search(
        from_airport="ist",
        to_airport="ayt",
        departure_date="2026-09-14",
        airlines=["tk", "pc"],
    )

    query = capture["query"]
    assert list(query.flight_data[0].airlines) == ["TK", "PC"]
    assert out["query"]["airlines"] == ["TK", "PC"]


def test_no_airlines_filter_means_mixed_search(monkeypatch):
    capture: dict = {}
    _stub_fetch_and_parse(monkeypatch, capture)

    out = search(
        from_airport="ist",
        to_airport="ayt",
        departure_date="2026-09-14",
    )

    query = capture["query"]
    assert list(query.flight_data[0].airlines) == []
    assert "airlines" not in out["query"]

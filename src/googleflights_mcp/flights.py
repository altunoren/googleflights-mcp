"""Pure flight-search logic for googleflights-mcp.

This module is intentionally independent from MCP: it can be imported and
called directly (see the Section 9 verification snippet in the build spec).

It bypasses the default `fast_flights.get_flights` fetcher because requests
originating from the EU/Turkey are frequently redirected to Google's
"before you continue" consent page, which the upstream parser cannot handle
(it raises `AttributeError: 'NoneType' object has no attribute 'text'`).
Instead we send our own request with consent-bypass cookies and hand the
resulting HTML to `fast_flights.parser.parse` ourselves.
"""

from __future__ import annotations

from typing import Any

from primp import Client

from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.parser import ResultList, SingleFlight, parse
from fast_flights.querying import Query

GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights"

# Cookies that skip the "before you continue" consent interstitial.
CONSENT_COOKIES = (
    "CONSENT=YES+cb.20210328-17-p0.en+FX+410; "
    "SOCS=CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwMTA5"
    "LjA3X3AwGgJlbiADGgYIgOe_rQY"
)

_VALID_TRIPS = {"one-way", "round-trip"}
_VALID_SEATS = {"economy", "premium-economy", "business", "first"}


def fmt_dt(sd: Any) -> str:
    """Format a `fast_flights` `SimpleDatetime` as `YYYY-MM-DD HH:MM`."""
    y, m, d = sd.date
    hh, mm = sd.time
    return f"{y:04d}-{m:02d}-{d:02d} {hh:02d}:{mm:02d}"


def fetch_and_parse(query: Query) -> ResultList:
    """Fetch Google Flights results for `query`, bypassing the consent wall."""
    client = Client(
        impersonate="chrome_145",
        impersonate_os="macos",
        referer=True,
        cookie_store=True,
    )
    params = dict(query.params())
    params.setdefault("hl", "en")
    params.setdefault("gl", "US")

    res = client.get(
        GOOGLE_FLIGHTS_URL,
        params=params,
        headers={"Cookie": CONSENT_COOKIES},
    )
    html = res.text
    if "before you continue" in html.lower():
        raise RuntimeError(
            "Google consent wall not bypassed (received the 'before you "
            "continue' interstitial). Consent cookies may be stale."
        )
    return parse(html)


def _leg_dict(leg: SingleFlight) -> dict:
    return {
        "from": leg.from_airport.code,
        "to": leg.to_airport.code,
        "departure": fmt_dt(leg.departure),
        "arrival": fmt_dt(leg.arrival),
        "duration_minutes": leg.duration,
        "plane_type": leg.plane_type,
    }


def _duration_label(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def normalize(result: ResultList, currency: str) -> list[dict]:
    """Convert a `fast_flights` `ResultList` into the spec's JSON shape."""
    airline_names = {a.code: a.name for a in result.metadata.airlines}

    normalized = []
    for f in result:
        stops = len(f.flights) - 1
        total_minutes = sum(leg.duration for leg in f.flights)
        first_leg = f.flights[0]
        last_leg = f.flights[-1]

        normalized.append(
            {
                "airlines": [airline_names.get(code, code) for code in f.airlines],
                "price": f.price,
                "currency": currency,
                "stops": stops,
                "stops_label": "direkt" if stops == 0 else f"{stops} aktarma",
                "departure": fmt_dt(first_leg.departure),
                "arrival": fmt_dt(last_leg.arrival),
                "duration_minutes": total_minutes,
                "duration_label": _duration_label(total_minutes),
                "legs": [_leg_dict(leg) for leg in f.flights],
                "carbon_grams": f.carbon.emission,
                "carbon_vs_typical_grams": f.carbon.typical_on_route,
            }
        )

    normalized.sort(key=lambda item: item["price"])
    return normalized


def search(
    from_airport: str,
    to_airport: str,
    departure_date: str,
    return_date: str | None = None,
    trip: str = "one-way",
    seat: str = "economy",
    adults: int = 1,
    children: int = 0,
    currency: str = "USD",
    max_results: int = 20,
    max_stops: int | None = None,
    airlines: list[str] | None = None,
) -> dict:
    """Search Google Flights and return results sorted by price ascending.

    `airlines` filters results to specific 2-letter IATA airline codes
    (e.g. `["TK"]` or `["TK", "PC"]`). Leave it `None` (the default) to
    search across all airlines, mixed together in one result list.
    """
    from_airport = from_airport.upper()
    to_airport = to_airport.upper()
    airlines = [code.upper() for code in airlines] if airlines else None

    if return_date:
        trip = "round-trip"

    if trip not in _VALID_TRIPS:
        return {
            "error": f"Invalid trip type '{trip}'. Must be one of {sorted(_VALID_TRIPS)}.",
            "query": {"from": from_airport, "to": to_airport, "departure_date": departure_date},
        }
    if seat not in _VALID_SEATS:
        return {
            "error": f"Invalid seat type '{seat}'. Must be one of {sorted(_VALID_SEATS)}.",
            "query": {"from": from_airport, "to": to_airport, "departure_date": departure_date},
        }
    if trip == "round-trip" and not return_date:
        return {
            "error": "return_date is required for round-trip searches.",
            "query": {"from": from_airport, "to": to_airport, "departure_date": departure_date},
        }

    query_summary = {
        "from": from_airport,
        "to": to_airport,
        "departure_date": departure_date,
        "trip": trip,
        "seat": seat,
        "currency": currency,
    }
    if return_date:
        query_summary["return_date"] = return_date
    if airlines:
        query_summary["airlines"] = airlines

    flight_queries = [
        FlightQuery(
            date=departure_date,
            from_airport=from_airport,
            to_airport=to_airport,
            airlines=airlines,
        )
    ]
    if trip == "round-trip" and return_date:
        flight_queries.append(
            FlightQuery(
                date=return_date,
                from_airport=to_airport,
                to_airport=from_airport,
                airlines=airlines,
            )
        )

    try:
        query = create_query(
            flights=flight_queries,
            seat=seat,
            trip=trip,
            passengers=Passengers(adults=adults, children=children),
            currency=currency,
            max_stops=max_stops,
        )
        result = fetch_and_parse(query)
    except Exception as exc:  # noqa: BLE001 - surfaced as a structured tool error
        return {"error": f"Flight search failed: {exc}", "query": query_summary}

    if not result:
        return {
            "error": f"No flights found for {from_airport} -> {to_airport} on {departure_date}",
            "query": query_summary,
        }

    options = normalize(result, currency=currency)
    if max_stops is not None:
        options = [o for o in options if o["stops"] <= max_stops]
    options = options[:max_results]

    if not options:
        return {
            "error": (
                f"No flights found for {from_airport} -> {to_airport} on "
                f"{departure_date} matching the given filters"
            ),
            "query": query_summary,
        }

    return {
        "query": query_summary,
        "count": len(options),
        "cheapest_price": options[0]["price"],
        "results": options,
    }

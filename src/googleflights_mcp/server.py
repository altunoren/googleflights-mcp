"""FastMCP stdio server exposing the `search_flights` tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .flights import search

mcp = FastMCP("googleflights")


@mcp.tool()
def search_flights(
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
    """Search Google Flights for available flights between two airports.

    Airport codes are 3-letter IATA codes (e.g. IST, AYT, JFK).
    Dates are YYYY-MM-DD. Returns structured flight options sorted by price.

    `airlines` optionally restricts results to specific 2-letter IATA
    airline codes, e.g. ["TK"] for Turkish Airlines only, or ["TK", "PC"]
    for Turkish Airlines + Pegasus. Omit it (or pass None/empty) to search
    all airlines mixed together in one result list.
    """
    return search(
        from_airport=from_airport,
        to_airport=to_airport,
        departure_date=departure_date,
        return_date=return_date,
        trip=trip,
        seat=seat,
        adults=adults,
        children=children,
        currency=currency,
        max_results=max_results,
        max_stops=max_stops,
        airlines=airlines,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

# googleflights-mcp

**Search Google Flights from Claude, Codex, or any MCP client — running
entirely on your own machine.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple)](https://modelcontextprotocol.io)

A local **stdio MCP server** that searches Google Flights and returns
structured, price-sorted flight options — no central server, no hosting
cost, no shared-IP ban risk, no API key. Every user runs their own copy on
their own IP.

Exposes one tool: **`search_flights`**.

```json
{
  "count": 5,
  "cheapest_price": 2715,
  "results": [
    {
      "airlines": ["Turkish Airlines"],
      "price": 2715,
      "currency": "TRY",
      "stops": 0,
      "stops_label": "direkt",
      "departure": "2026-09-14 21:15",
      "arrival": "2026-09-14 22:40",
      "duration_label": "1h 25m"
    }
  ]
}
```

## Table of contents

- [Why this exists](#why-this-exists)
- [Installation](#installation)
- [Client configuration](#client-configuration)
- [Usage example](#usage-example)
- [`search_flights` reference](#search_flights-reference)
- [How the Google consent wall is handled](#how-the-google-consent-wall-is-handled)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Legal notice](#legal-notice)

## Why this exists

Google doesn't offer a public Flights API. `googleflights-mcp` scrapes the
same public web interface Google Flights itself uses, wraps it in the
[Model Context Protocol](https://modelcontextprotocol.io), and runs as a
**local** process launched by your MCP client — so your assistant can search
real flight prices without a hosted backend or shared API key.

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/altunoren/googleflights-mcp.git
cd googleflights-mcp
pip install -e .
```

Or install isolated, without cloning:

```bash
pipx install git+https://github.com/altunoren/googleflights-mcp.git
# or
uv tool install git+https://github.com/altunoren/googleflights-mcp.git
```

Any of these gives you the `googleflights-mcp` command on your `PATH`.

## Client configuration

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "googleflights": {
      "command": "googleflights-mcp"
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add googleflights -- googleflights-mcp
```

### Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.googleflights]
command = "googleflights-mcp"
args = []
```

> If `googleflights-mcp` isn't on your client's `PATH` (common with
> `pipx`/`uv tool` installs or restricted app sandboxes), use the absolute
> path instead — e.g. `python -m googleflights_mcp`, or the full path to the
> binary inside your virtualenv (`/path/to/venv/bin/googleflights-mcp`).

## Usage example

Just ask your assistant naturally:

> "List one-way economy flights from IST to AYT on September 14th, in TRY."

The model calls `search_flights` and returns options sorted by price,
cheapest first.

## `search_flights` reference

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `from_airport` | str | yes | — | 3-letter IATA departure code (e.g. `IST`) |
| `to_airport` | str | yes | — | 3-letter IATA arrival code (e.g. `AYT`) |
| `departure_date` | str | yes | — | `YYYY-MM-DD` |
| `return_date` | str | no | `None` | `YYYY-MM-DD`; if given, `trip` becomes `round-trip` |
| `trip` | str | no | `one-way` | `one-way` \| `round-trip` |
| `seat` | str | no | `economy` | `economy` \| `premium-economy` \| `business` \| `first` |
| `adults` | int | no | `1` | Number of adults |
| `children` | int | no | `0` | Number of children |
| `currency` | str | no | `USD` | ISO currency code (e.g. `TRY`, `EUR`) |
| `max_results` | int | no | `20` | Max number of options to return |
| `max_stops` | int | no | `None` | Max connections (0 = nonstop only) |

Each result includes airline names, price, stop count, departure/arrival
times, per-leg detail, total duration, and estimated carbon emissions vs. the
route's typical emissions. Errors (no flights found, network failure,
consent wall not bypassed) come back as `{"error": "...", "query": {...}}`
instead of raising, so a failed search never crashes your MCP session.

## How the Google consent wall is handled

Requests originating from the EU/Turkey are frequently redirected to
Google's `consent.google.com` "before you continue" cookie page. This
project does **not** use `fast_flights.get_flights`'s default fetcher, which
breaks on that page (`AttributeError: 'NoneType' object has no attribute
'text'`). Instead it sends its own request with consent-bypass cookies and
parses the resulting HTML directly — see
[`src/googleflights_mcp/flights.py`](src/googleflights_mcp/flights.py). If
Google changes its consent flow and the bypass stops working, the tool
returns a clear `{"error": "..."}` instead of crashing.

## Development

```bash
pip install -e '.[dev]'
pytest -q            # fast tests, no network
pytest -q -m live     # includes a live Google Flights smoke test
```

`src/googleflights_mcp/flights.py` has no MCP dependency — you can import
and call `search(...)` directly:

```python
from googleflights_mcp.flights import search
import datetime as dt, json

d = (dt.date.today() + dt.timedelta(days=14)).isoformat()
out = search(from_airport="IST", to_airport="AYT", departure_date=d,
             trip="one-way", seat="economy", currency="TRY", max_results=5)
print(json.dumps(out, ensure_ascii=False, indent=2))
```

Project layout:

```
src/googleflights_mcp/
├── __init__.py
├── __main__.py     # `python -m googleflights_mcp`
├── server.py        # FastMCP + search_flights tool
└── flights.py       # fetch + parse + normalize (MCP-independent)
tests/
├── test_normalize.py    # no network, always runs
└── test_smoke_live.py   # live network, opt-in via `-m live`
```

## Troubleshooting

**`{"error": "Google consent wall not bypassed ..."}`**
The bundled consent cookies may be stale. Open an issue with the date and
your region — a cookie refresh is usually a one-line fix.

**`{"error": "No flights found for ..."}`**
Either the route/date genuinely has no results, or Google served an
unexpected page layout. Try a well-known route (e.g. `IST` → `AYT`) to
confirm the server itself is working.

**Client can't find the `googleflights-mcp` command**
Use an absolute path in your client config — see the note under
[Client configuration](#client-configuration).

## Legal notice

This tool scrapes Google Flights' public web interface — it is **not** an
official Google API. It's intended for personal/local use only. Heavy
automated request volume can lead to IP blocking. Compliance with Google's
Terms of Service is your responsibility.

## License

[MIT](LICENSE)

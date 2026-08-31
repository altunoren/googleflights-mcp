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
- [What can you use it for?](#what-can-you-use-it-for)
- [Installation](#installation)
- [Client configuration](#client-configuration)
- [How to use it](#how-to-use-it)
- [`search_flights` reference](#search_flights-reference)
- [Recipes for power users](#recipes-for-power-users)
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

## What can you use it for?

Once it's connected, your assistant can answer real travel questions by
actually querying Google Flights — not guessing from training data. A few
concrete things people use it for:

- **Find the cheapest option, fast** — "what's the cheapest flight from IST
  to AYT next Friday?" gets a real, price-sorted answer in one round trip.
- **Compare a handful of dates before booking** — ask the assistant to check
  3–5 candidate dates in a row (or see the [scripted version](#recipe-cheapest-day-to-fly)
  below) to spot the cheapest day to fly without opening a browser tab per
  date.
- **Plan round trips** — pass both `departure_date` and `return_date` and
  get a real round-trip fare instead of adding two one-ways together.
- **Stick to an airline (or alliance)** — loyalty-program members can filter
  to `airlines: ["TK"]` or compare two carriers head-to-head with
  `["TK", "PC"]`. See [Filtering by airline](#filtering-by-airline).
- **Direct flights only** — business travelers or anyone avoiding layovers
  can set `max_stops: 0`.
- **Book for a group** — `adults`/`children` produce real per-passenger
  pricing instead of a single-traveler estimate.
- **Shop in your own currency** — set `currency` to `TRY`, `EUR`, whatever
  you think in, instead of mentally converting from USD.
- **Compare cabins** — run the same search with `seat: "economy"` and then
  `seat: "business"` to see the real upgrade cost, not a rule-of-thumb
  multiplier.
- **Factor in carbon emissions** — every result includes `carbon_grams` and
  `carbon_vs_typical_grams`, so an assistant can point out the
  lower-emission option on a route, not just the cheapest one.
- **Automate price-watching** — since `flights.py` has zero MCP dependency,
  you can `import` and call `search()` from your own script or cron job
  (see [Recipes](#recipes-for-power-users)) to track a route's price over
  time — no separate scraping code to maintain.
- **General travel-assistant conversations** — trip planning, "which is
  cheaper, flying into JFK or EWR," multi-city comparisons — anything you'd
  ask a human travel agent, phrased naturally in chat.

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

## How to use it

You don't call the tool yourself — you just talk to your assistant, and it
maps your request onto `search_flights`'s parameters. Some example prompts,
grouped by what they exercise:

| You ask | What happens under the hood |
|---|---|
| "List one-way economy flights from IST to AYT on September 14th, in TRY." | `trip="one-way"`, `seat="economy"`, `currency="TRY"` |
| "Gidiş-dönüş, 20 Ekim gidiş 27 Ekim dönüş, IST-AYT" | `return_date` set → `trip` auto-switches to `round-trip` |
| "Only Turkish Airlines flights from IST to AYT" | `airlines=["TK"]` — see [Filtering by airline](#filtering-by-airline) |
| "Direct flights only, no layovers" | `max_stops=0` |
| "2 adults 1 child, business class, IST to JFK" | `adults=2`, `children=1`, `seat="business"` |
| "What's the cheapest flight next Friday?" | assistant resolves "next Friday" to `YYYY-MM-DD` itself |
| "Which option produces less CO2?" | assistant compares `carbon_grams` across the returned `results` |

Whatever you ask, the model calls `search_flights` and gets back options
sorted by price, cheapest first — it doesn't have to guess, it's reading a
real Google Flights response.

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
| `airlines` | list[str] | no | `None` | 2-letter IATA airline codes to filter by (e.g. `["TK"]`). Omit for all airlines, mixed. |

Each result includes airline names, price, stop count, departure/arrival
times, per-leg detail, total duration, and estimated carbon emissions vs. the
route's typical emissions. Errors (no flights found, network failure,
consent wall not bypassed) come back as `{"error": "...", "query": {...}}`
instead of raising, so a failed search never crashes your MCP session.

### Filtering by airline

`airlines` takes a list of 2-letter IATA **airline** codes (not airport
codes) — e.g. `TK` for Turkish Airlines, `PC` for Pegasus, `BA` for British
Airways. Three ways to use it:

- **One specific airline** — `airlines: ["TK"]` returns only Turkish
  Airlines flights.
- **Several specific airlines** — `airlines: ["TK", "PC"]` returns flights
  from either carrier, still sorted together by price.
- **Mixed / all airlines (default)** — omit `airlines` entirely (or pass
  `null`/an empty list). You'll get every airline serving the route, mixed
  in one price-sorted list — which is what the example at the top of this
  README shows.

Verified against a live search (`IST` → `LHR`): no filter returned Turkish
Airlines, British Airways, Austrian, and LOT mixed together; `airlines:
["TK"]` returned only Turkish Airlines; `airlines: ["BA"]` returned only
British Airways.

> Ask your assistant in plain language too — e.g. "IST'ten LHR'ye sadece
> British Airways ile" or "only show Turkish Airlines and Pegasus flights" —
> the model will map that to the `airlines` parameter for you.

## Recipes for power users

`src/googleflights_mcp/flights.py` has zero MCP dependency, so you can drive
it directly from a plain Python script — useful for anything beyond a
single chat query.

### Recipe: cheapest day to fly

Check a whole date range and find the cheapest day to depart:

```python
import datetime as dt
from googleflights_mcp.flights import search

start = dt.date.today() + dt.timedelta(days=14)
candidates = []

for offset in range(7):  # check a week of candidate dates
    d = (start + dt.timedelta(days=offset)).isoformat()
    out = search(from_airport="IST", to_airport="AYT", departure_date=d,
                 currency="TRY", max_results=1)
    if "error" not in out:
        candidates.append((d, out["cheapest_price"]))

candidates.sort(key=lambda c: c[1])
for date, price in candidates:
    print(f"{date}: {price} TRY")
```

### Recipe: compare two airlines head-to-head

```python
from googleflights_mcp.flights import search

for code, name in [("TK", "Turkish Airlines"), ("PC", "Pegasus")]:
    out = search(from_airport="IST", to_airport="AYT", departure_date="2026-09-14",
                 currency="TRY", airlines=[code], max_results=1)
    price = out.get("cheapest_price", "no flights")
    print(f"{name}: {price}")
```

### Recipe: price-watch cron job

Run the date-range check above on a schedule (cron, GitHub Actions, a
`launchd`/systemd timer, or Claude Code's own `/loop`/`schedule` skills if
you're driving this from an agent) and alert yourself — email, Slack
webhook, whatever you prefer — whenever `cheapest_price` drops below a
threshold you set. Because `search()` returns plain dicts, wiring it into
any alerting pipeline is just a few lines.

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

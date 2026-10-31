# ✈️ azair-eu-mcp

[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-server-7B3FF2)](https://modelcontextprotocol.io)
[![uv](https://img.shields.io/badge/uv-managed-purple)](https://docs.astral.sh/uv/)
[![azair.eu](https://img.shields.io/badge/integration-azair.eu-1d76db)](https://www.azair.eu)

MCP server for [azair.eu](https://www.azair.eu) — cheap flight search across European low-cost airlines with flexible dates. Give your AI assistant the power to hunt for bargain flights the way humans do on azair: loose date ranges, multiple airports, metro areas, and every advanced filter from the azair search form.

## Features

- 🔎 **Flexible-date search** — the core azair superpower: pick a date *range*, get the cheapest day combinations within it
- 🛫 **Multi-airport search** — search from several airports at once (e.g. `PRG` + `BRQ` + `NUE`)
- 🏙️ **Metro-area search** — cover all airports of a city via metro codes (e.g. `MIL_ALL` → MXP, BGY, LIN)
- 🌍 **Anywhere mode** — destination `XXX` searches the whole continent
- ⚙️ **All advanced filters** — weekdays, time windows, stopover length, transfers, Schengen-only, clubs, and more
- 💱 **Multi-currency** — EUR, USD, GBP, PLN, CZK, and all azair currencies
- ✍️ **Structured results** — clean JSON with prices, dates, per-segment flight details, and booking links

## Quick start

Ask your assistant (Claude, Cursor, Windsurf, …):

> Find cheap return flights from Prague to anywhere in Italy between August and January, min 5 nights, max 8 nights, any Milan or Rome airport.

or directly:

```
search_flights(src_airport="PRG", src_airports=["BRQ", "NUE"],
               dst_airport="MXP", dst_airports=["LIN", "BGY"], dst_metro_code="MIL_ALL",
               dep_date="2026-08-01", arr_date="2027-01-31",
               min_days_stay=5, max_days_stay=8)
```

Example response:

```json
{
  "total_price": 33.33,
  "currency": "EUR",
  "length_of_stay_days": 6,
  "outbound_date": "Thu 20/08/26",
  "return_date": "Wed 26/08/26",
  "outbound_segments": [
    {
      "airline": "Ryanair",
      "airline_iata": "FR",
      "flight_number": "FR3601",
      "departure_airport": "Prague",
      "departure_airport_code": "PRG",
      "departure_time": "09:00",
      "arrival_airport": "Bologna",
      "arrival_airport_code": "BLQ",
      "arrival_time": "10:30",
      "duration": "12:10 h / 1 change",
      "price": 33.33,
      "currency": "EUR"
    }
  ],
  "return_segments": [],
  "booking_url": "book/b.php?b=RlJQUkdCTFEyNjA4MjUzNjAxMTAwMjAyNi0wOC0wMSswMjoxM2Vud3d3LmF6YWlyLmV1"
}
```

Returns up to 180 results, each with total price, dates, outbound/return segments (airline, flight number, times, duration, leg price), and a direct booking URL.

## Tools

### `search_flights`

Full-featured flight search mirroring the azair search form, including advanced parameters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `src_airport` | string | — | Source airport IATA code (e.g. `WMI`, `STN`). Metro/region codes such as `MIL_ALL`, `PAR_ALL`, `IT`, `BALTIC` are expanded automatically |
| `dst_airport` | string | — | Destination IATA code, `XXX` for anywhere, or a metro/region code such as `MIL_ALL`, `PAR_ALL`, `IT`, `BALTIC` |
| `src_airports` | string[] | — | Additional source airports, e.g. `BRQ`, `NUE` together with `PRG` |
| `dst_airports` | string[] | — | Additional destination airports, e.g. `LIN`, `BGY` together with `MXP` |
| `src_metro_code` | string | — | Source metro/region code covering several airports, e.g. `MIL_ALL`, `LON_ALL`, `IT`; expanded automatically |
| `dst_metro_code` | string | — | Destination metro/region code covering several airports, e.g. `MIL_ALL`, `PAR_ALL`, `LON_ALL`, `IT`; expanded automatically |
| `dep_date` | string | — | Earliest departure, `DD.MM.YYYY` or `YYYY-MM-DD` |
| `arr_date` | string | — | Latest return, `DD.MM.YYYY` or `YYYY-MM-DD` |
| `min_days_stay` | int | `2` | Minimum trip length in days |
| `max_days_stay` | int | `7` | Maximum trip length in days |
| `adults` | int | `1` | Adults (1-9) |
| `children` | int | `0` | Children (0-8) |
| `infants` | int | `0` | Infants (0-8) |
| `currency` | string | `EUR` | `EUR`, `USD`, `GBP`, `PLN`, `CZK`, … |
| `max_changes` | int | `1` | Max stopovers per leg (0-3, `0` = direct flights only) |
| `is_oneway` | bool | `false` | One-way instead of return |
| `schengen_only` | bool | `false` | Only transfers inside the Schengen area |
| `allow_transfer` | bool | `false` | Allow ground transfer between airports; automatically enabled for open-jaw searches (`same_arr=false`/`same_dep=false`) with a specific destination |
| `departure_weekdays` | int[] | all | Departure weekdays, `0=Mon..6=Sun` |
| `return_weekdays` | int[] | all | Return weekdays |
| `min_hour_outbound` | string | `0:00` | Earliest outbound time |
| `max_hour_outbound` | string | `24:00` | Latest outbound time |
| `min_hour_inbound` | string | `0:00` | Earliest inbound time |
| `max_hour_inbound` | string | `24:00` | Latest inbound time |
| `min_hour_stay` | string | `0:45` | Minimum stopover time |
| `max_hour_stay` | string | `23:20` | Maximum stopover time |
| `next_day` | int | `0` | Allow overnight stopovers |
| `same_dep` | bool | `true` | Return to the same departure airport |
| `same_arr` | bool | `true` | Return from the same arrival airport |

### `search_airports`

Resolve IATA codes, airport names, and metro/region codes before searching — useful for finding the right code for a city.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | IATA code, metro/region code, or partial name (e.g. `WMI`, `MIL_ALL`, `London`, `Barcelona`) |

Returns up to 50 matching airports and metro/region codes with code and name.

## Installation

```bash
git clone <repo-url> azair-eu-mcp
cd azair-eu-mcp
uv sync
```

## Usage

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "azair-eu-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/azair-eu-mcp", "python", "main.py"]
    }
  }
}
```

### Cursor / Windsurf

Add the same command in the MCP servers settings.

### Any MCP client

Run the server directly — it speaks MCP over stdio:

```bash
uv run python main.py
```

## Development

```bash
uv sync
uv run python main.py

# Offline regression tests
PYTHONPATH=. uv run python -m unittest discover -s tests -t . -v
```

Sanity-check a search without spinning up the server:

```bash
uv run python -c "
import asyncio
from azair.models import SearchParams
from azair.client import fetch_search_results
from azair.parser import parse_results

async def main():
    html = await fetch_search_results(SearchParams(
        src_airport='PRG', dst_airport='STN',
        dep_date='2026-08-01', arr_date='2026-08-31',
    ))
    print(len(parse_results(html)), 'results')

asyncio.run(main())
"
```

## How it works

- Azair exposes no public JSON API — results are scraped from the HTML search results page (`azfin.php`)
- The airport database is fetched once from azair's static JS asset and cached in memory
- Multi-airport and metro codes are sent as the azair web app does (bracket notation + `srcapN`/`dstapN` params)
- Open-jaw searches automatically set azair's `transfer` flag, which is required to search different arrival/return airports
- If azair returns nothing for a wide stay range (e.g. 1-3 days) even though shorter trips exist, the server retries a bounded number of narrower ranges and merges the results
- Transient empty responses from azair are retried once before falling back to narrower stay ranges, with an overall retry budget
- Metro and region codes set azair's `srcMC`/`dstMC` field, which is required for some country/region searches

## Notes

- Search times vary (10-60s) depending on the query scope
- Azair's `XXX` (anywhere) mode does not support open-jaw trips; it returns same-airport round-trips

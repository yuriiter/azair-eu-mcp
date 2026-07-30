# azair-eu-mcp

MCP server for [azair.eu](https://www.azair.eu) — search cheap flights across European low-cost airlines with flexible dates.

## Tools

### `search_flights`

Full-featured flight search mirroring all azair form parameters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `src_airport` | string | — | IATA code (e.g. `WMI`, `STN`) |
| `dst_airport` | string | — | IATA code or `XXX` for anywhere |
| `dep_date` | string | — | Earliest departure, `DD.MM.YYYY` or `YYYY-MM-DD` |
| `arr_date` | string | — | Latest return, `DD.MM.YYYY` or `YYYY-MM-DD` |
| `min_days_stay` | int | `2` | Minimum trip length |
| `max_days_stay` | int | `7` | Maximum trip length |
| `adults` | int | `1` | Number of adults (1-9) |
| `children` | int | `0` | (0-8) |
| `infants` | int | `0` | (0-8) |
| `currency` | string | `EUR` | `EUR`, `USD`, `GBP`, `PLN`, `CZK`, etc. |
| `max_changes` | int | `1` | Max stopovers (1-3) |
| `is_oneway` | bool | `false` | One-way or return |
| `schengen_only` | bool | `false` | Only Schengen transfers |
| `allow_transfer` | bool | `false` | Allow ground transfer |
| `departure_weekdays` | int[] | all | Departure days `0=Mon..6=Sun` |
| `return_weekdays` | int[] | all | Return days |
| `min_hour_outbound` | string | `0:00` | Earliest outbound time |
| `max_hour_outbound` | string | `24:00` | Latest outbound time |
| `min_hour_inbound` | string | `0:00` | Earliest inbound time |
| `max_hour_inbound` | string | `24:00` | Latest inbound time |
| `min_hour_stay` | string | `0:45` | Min stopover time |
| `max_hour_stay` | string | `23:20` | Max stopover time |
| `next_day` | int | `0` | Allow overnight stopovers (max days) |
| `same_dep` | bool | `true` | Return to same departure airport |
| `same_arr` | bool | `true` | Return from same arrival airport |

Returns up to 180 results with price, dates, segments (airline, flight number, times, duration, leg price), and booking URL.

### `search_airports`

Search airports by IATA code or name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | IATA code or partial name (e.g. `WMI`, `London`, `Barcelona`) |

Returns matching airports with code and name.

## Installation

```bash
git clone <repo-url> azair-eu-mcp
cd azair-eu-mcp
uv sync
```

## Usage

Run the server:

```bash
uv run python main.py
```

### Claude Desktop config

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

Add the server in your MCP config pointing to the same command.

## Notes

- Azair uses an expired SSL certificate — the server bypasses SSL verification.
- The airport database is fetched once from azair's static JS and cached in memory.
- Flight data is scraped from HTML (azair has no public JSON API).
- Search times vary (10-60s) depending on the query scope.

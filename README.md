# sdmx-data-mcp

[![PyPI](https://img.shields.io/pypi/v/sdmx-data-mcp)](https://pypi.org/project/sdmx-data-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/sdmx-data-mcp)](https://pypi.org/project/sdmx-data-mcp/)
[![CI](https://github.com/markchweya/sdmx-data-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/markchweya/sdmx-data-mcp/actions/workflows/ci.yml)
[![Licence](https://img.shields.io/pypi/l/sdmx-data-mcp)](LICENSE)

An [MCP](https://modelcontextprotocol.io) server that lets an AI assistant
discover **and retrieve** official statistics from SDMX services.

Built on the BIS's own [pysdmx](https://github.com/bis-med-it/pysdmx) library.

## Why this exists

Other SDMX MCP servers navigate metadata well and then hand back a *query URL*.
The assistant ends up with a link, not numbers — and cannot answer the question
it was asked.

`sdmx-data-mcp` finishes the job. `get_data` returns the observations.

## Quick start

```bash
pip install sdmx-data-mcp
```

Then register it with your client:

```bash
claude mcp add sdmx -- sdmx-data-mcp
```

That is the whole setup. Ask your assistant something like *"what is the Swiss
policy rate since 2020?"* and it will find the dataflow, check what it can
filter on, and come back with the actual series.

<details>
<summary>Other clients</summary>

**Claude Desktop** — in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sdmx": {
      "command": "sdmx-data-mcp"
    }
  }
}
```

**Cursor** — in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sdmx": {
      "command": "sdmx-data-mcp"
    }
  }
}
```

If `sdmx-data-mcp` is not on your `PATH`, use the absolute path to the
executable, or `"command": "python", "args": ["-m", "sdmx_data_mcp"]`.

**Over HTTP**, to share one instance:

```bash
sdmx-data-mcp --transport http --host 127.0.0.1 --port 8000
```

</details>

## The four tools

Meant to be called in order. Only the last one moves data.

| Tool | Purpose |
| --- | --- |
| `list_services` | Known endpoints, plus any SDMX-REST v2 base URL you supply |
| `search_dataflows` | One `dataflows()` call, then local term matching |
| `inspect_dataflow` | Components, available codes, size signals |
| `get_data` | **Retrieves the observations** |

## A real session

Transcripts below are actual tool output, not illustrations. More in
[docs/EXAMPLES.md](docs/EXAMPLES.md).

### 1. Find the dataflow

```jsonc
search_dataflows(query="policy rate central bank")

{
  "search_terms": ["policy", "rate", "central", "bank"],
  "total_dataflows_on_service": 32,
  "match_count": 12,
  "dataflows": [
    { "ref": "BIS:WS_CBPOL(1.0)", "name": "Central bank policy rates",
      "matched_on": "name" },
    { "ref": "BIS:WS_CBS_PUB(1.0)", "name": "Consolidated banking",
      "matched_on": "name" }
    // ...
  ]
}
```

One request to the service; the terms are matched locally. Searching for
synonyms costs nothing extra, so put them all in one query.

### 2. See what you can filter on

```jsonc
inspect_dataflow(ref="BIS:WS_CBPOL(1.0)", find_code="CH")

{
  "series_count": 98,
  "obs_count": null,          // BIS does not report this
  "size_warning": null,       // small enough to retrieve
  "dimensions": [
    { "id": "FREQ", "name": "Frequency", "code_count": 2,
      "codes": [{"id": "D", "name": "Daily"}, {"id": "M", "name": "Monthly"}] },
    { "id": "REF_AREA", "name": "Reference area", "code_count": 49,
      "codes": [ /* ... */ {"id": "CH", "name": "Switzerland"} /* ... */ ] }
  ]
}
```

### 3. Get the numbers

```jsonc
get_data(
  ref="BIS:WS_CBPOL(1.0)",
  filters="FREQ = 'M' AND REF_AREA = 'CH' AND TIME_PERIOD >= '2020-01'",
  columns=["OBS_VALUE"],
)

{
  "filter_applied": "FREQ = 'M' AND REF_AREA = 'CH' AND TIME_PERIOD >= '2020-01'",
  "filter_fallback": null,
  "row_count": 79,
  "total_rows_available": 79,
  "truncated": false,
  "records": [
    {"SERIES_KEY": "M.CH", "OBS_VALUE": "-0.75", "TIME_PERIOD": "2020-01"},
    {"SERIES_KEY": "M.CH", "OBS_VALUE": "-0.75", "TIME_PERIOD": "2020-02"}
    // ...
  ],
  "next_step": "Complete: all 79 matching rows were returned. Safe to aggregate."
}
```

`truncated: false` and `row_count == total_rows_available`, so this really is
the whole series and it is safe to average or chart.

### Several values of one component

The query parser accepts `AND` but **not** `OR`. Use `IN (...)`:

```jsonc
get_data(
  ref="BIS:WS_XRU(1.0)",
  filters="FREQ = 'M' AND CURRENCY IN ('CHF', 'KES') AND TIME_PERIOD >= '2026-01'",
  columns=["OBS_VALUE"],
)

{ "row_count": 14, "truncated": false, "records": [
  {"SERIES_KEY": "M.CH.CHF.E", "OBS_VALUE": "0.768269", "TIME_PERIOD": "2026-01"},
  {"SERIES_KEY": "M.KE.KES.A", "OBS_VALUE": "129.126615", "TIME_PERIOD": "2025-12"}
  // ...
] }
```

With both legs retrieved, an assistant can compute what neither service
publishes — a CHF/KES cross rate — and correctly note that the newest period
the two currencies *share* is December 2025, because KES lags CHF.

## What the server enforces

These rules are handled by the server rather than left for the assistant to
remember. Each one prevents a specific class of confidently wrong answer.

**Conjunctions only.** `AND` between clauses, never `OR`. Several values of one
component use `IN ('A', 'B')`.

**Availability is not validity.** `inspect_dataflow` reports codes for which
data *currently exist*. A code missing from that list may still be valid in the
full codelist, so its absence is never reported as proof that something does
not exist.

**Ambiguous codes are surfaced, not guessed.** On BIS consolidated banking,
`CH` is available in three components at once — reporting country, counterparty
country, and a bank type that happens to share the country codelist:

```jsonc
inspect_dataflow(ref="BIS:WS_CBS_PUB(1.0)", find_code="CH")

{ "code_locations": [
    {"component_id": "L_REP_CTY",     "role_hint": "reporting country"},
    {"component_id": "CBS_BANK_TYPE", "role_hint": "bank type (shares a country codelist)"},
    {"component_id": "L_CP_COUNTRY",  "role_hint": "counterparty country"}
  ],
  "next_step": "That code is ambiguous - it appears in 3 components ..." }
```

Claims *by* Swiss banks and claims *on* Switzerland are different questions.
The server makes the assistant choose rather than silently pick one.

**Size before retrieval.** `obs_count` is frequently unreported — the BIS
returns `null` for it on both full and filtered scopes — so `series_count` is
the signal relied on. A `size_warning` appears when retrieval would truncate.

**Truncation is not sampling.** When `truncated` is true, the rows are the
first N in service order, and `next_step` says so explicitly:

> Truncated: 112,648 rows matched but only 500 were returned. These are the
> first rows in service order, not a sample — do not compute totals or averages
> from them.

**Time filters degrade gracefully.** `TIME_PERIOD` is pushed down to the
service first. On a client-side rejection the clause is stripped, the narrower
query is retried, and the cutoff is applied with pandas — reported in
`filter_fallback`. It deliberately does *not* fall back on `NotFound`,
`Unavailable` or `InternalError`, where dropping a clause cannot help and would
only obscure the real error.

**Errors keep their meaning.** The pysdmx error hierarchy is preserved rather
than flattened, so an assistant can tell a transient outage from a bad
reference instead of retrying blindly or giving up too early:

```text
[internal_error] Unexpected message format - The payload could not be
deserialized. | retriable=false | next_step: The service failed, or returned a
response that could not be parsed. Do not repeat the identical call - narrow
the filter or try a different dataflow, since the fault is server-side.
```

| Kind | Retriable | Means |
| --- | --- | --- |
| `unavailable` | yes | Service unreachable; retry after a delay |
| `retriable_error` | yes | Transient failure |
| `not_found` | no | Resource does not exist; do not repeat |
| `invalid_request` | no | Malformed filter; check syntax and code IDs |
| `unauthorized` | no | Credentials rejected |
| `not_implemented` | no | Service lacks the required API |
| `internal_error` | no | Server-side fault; narrow or change the query |
| `unexpected_error` | no | Bug in this server; please report it |

## Services

`pysdmx.api.dc.Endpoints` currently ships exactly one endpoint, the BIS. Every
tool therefore takes a `service` argument accepting **any** SDMX-REST v2 base
URL as a first-class input, not a fallback:

```text
search_dataflows(query="prices", service="https://your-service.org/api/v2")
```

The service must return structural metadata as SDMX-JSON 2.0.0 and data as
SDMX-CSV. Other providers (ECB, OECD, IMF, Eurostat, ILO) are deliberately not
hardcoded: each needs verifying against those requirements first, and listing
them unverified would invite confident failures.

## Development

```bash
pip install -e ".[dev]"
ruff format && ruff check && mypy
pytest --cov=sdmx_data_mcp --cov-branch --cov-report=term-missing
```

162 tests at 100% statement and branch coverage, mypy in strict mode, CI across
Linux, Windows and macOS on Python 3.10–3.13.

Most server tests inject a fake connector so every branch is reachable
deterministically. A separate end-to-end module drives the real
`PandasConnector` against `respx`-mocked responses, so drift in URL
construction or SDMX-CSV parsing surfaces there.

## Relationship to pysdmx

This package depends on `pysdmx[data]` from PyPI. It does not fork or vendor
it, and uses only the public API — `PandasConnector`, `Endpoints` and the
errors hierarchy.

The same server has also been proposed upstream as
[bis-med-it/pysdmx#669](https://github.com/bis-med-it/pysdmx/pull/669). This
package exists so it is installable today regardless of what happens there.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

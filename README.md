# sdmx-data-mcp

An [MCP](https://modelcontextprotocol.io) server that lets an AI assistant
discover **and retrieve** official statistics from SDMX services.

Built on the BIS's own [pysdmx](https://github.com/bis-med-it/pysdmx) library.

## Why

Existing SDMX MCP servers navigate metadata well and then hand back a *query
URL*. The assistant ends up with a link, not numbers.

`sdmx-data-mcp` finishes the job: `get_data` returns the observations.

## Install

```bash
pip install sdmx-data-mcp
```

Python 3.10+.

## Configure your client

**Claude Code**

```bash
claude mcp add sdmx -- sdmx-data-mcp
```

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
executable in the environment where you installed it, or
`"command": "python", "args": ["-m", "sdmx_data_mcp"]`.

To share one instance over the network instead:

```bash
sdmx-data-mcp --transport http --host 127.0.0.1 --port 8000
```

## The four tools

Meant to be called in order.

| Tool | Purpose |
| --- | --- |
| `list_services` | Known endpoints, plus any SDMX-REST v2 base URL you supply |
| `search_dataflows` | One `dataflows()` call, then local term matching |
| `inspect_dataflow` | Components, available codes, size signals |
| `get_data` | **Retrieves the observations** |

## A worked example

Asking an assistant *"how much do Swiss banks have in foreign claims since
2020?"* drives this sequence against the BIS.

**1. Find the dataflow.**

```text
search_dataflows(query="consolidated banking")

-> ref: BIS:WS_CBS_PUB(1.0)
   name: Consolidated banking
   matched_on: name
```

**2. Work out what "Swiss" actually means here.**

```text
inspect_dataflow(ref="BIS:WS_CBS_PUB(1.0)", find_code="CH")

-> code_locations:
     L_REP_CTY      (reporting country)
     CBS_BANK_TYPE  (bank type (shares a country codelist))
     L_CP_COUNTRY   (counterparty country)
   series_count: 228370
   size_warning: This scope holds 228,370 series ...
   next_step: That code is ambiguous - it appears in 3 components ...
```

This is the step that prevents a confidently wrong answer. `CH` is available
in three different components of this dataflow, and each answers a different
question: claims *by* Swiss banks, claims *on* Switzerland, or a bank-type
code that happens to share the country codelist.

**3. Scope it, and check the size.**

```text
inspect_dataflow(
    ref="BIS:WS_CBS_PUB(1.0)",
    filters="L_MEASURE = 'S' AND L_REP_CTY = 'CH' AND FREQ = 'Q'",
)

-> series_count: 6671   (down from 228370)
```

If the question was only *whether* data exist, the answer is already here.

**4. Retrieve the numbers.**

```text
get_data(
    ref="BIS:WS_CBS_PUB(1.0)",
    filters="L_MEASURE = 'S' AND L_REP_CTY = 'CH' AND FREQ = 'Q'"
            " AND TIME_PERIOD >= '2020-Q1'",
    columns=["OBS_VALUE"],
    limit=500,
)

-> row_count: 500
   total_rows_available: 112648
   truncated: true
   next_step: Truncated: 112,648 rows matched but only 500 were returned.
              These are the first rows in service order, not a sample ...
```

## Services

`pysdmx.api.dc.Endpoints` currently ships exactly one endpoint, the BIS. Every
tool therefore takes a `service` argument accepting **any** SDMX-REST v2 base
URL as a first-class input:

```text
search_dataflows(query="prices", service="https://your-service.org/api/v2")
```

The service must return structural metadata as SDMX-JSON 2.0.0 and data as
SDMX-CSV. Other providers (ECB, OECD, IMF, Eurostat, ILO) are deliberately not
hardcoded, because each needs verifying against those requirements first, and
listing them unverified would invite confident failures.

## Design notes

The non-obvious SDMX rules are enforced by the server rather than left for the
assistant to remember.

**Conjunctions only.** The query parser supports `AND`. Never generate `OR`;
for several values of one component use `IN ('A', 'B')`.

**Availability is not validity.** `inspect_dataflow` reports codes for which
data currently exist. A code absent from that list may still be valid in the
full codelist, so its absence is not evidence that something does not exist.

**Size before retrieval.** `obs_count` is frequently unreported — the BIS
returns `None` for it, on both full and filtered scopes — so `series_count`
is the signal relied on. Tools warn when a scope is large enough to truncate.

**Truncation is not sampling.** When `truncated` is true, the rows returned
are the first ones in service order. They must not be aggregated as though
they were a representative sample.

**Time filters degrade gracefully.** `TIME_PERIOD` comparisons are pushed
down to the service first. If the service rejects the query with a client
error, the clause is stripped, the narrower query is retried, and the cutoff
is applied with pandas — reported in `filter_fallback`. It deliberately does
*not* fall back on `NotFound`, `Unavailable` or `InternalError`, where
dropping a clause cannot help and would only obscure the real error.

**Errors keep their meaning.** The pysdmx error hierarchy is preserved rather
than flattened, so an assistant can tell a transient outage (`unavailable`,
retriable) from a bad reference (`not_found`, not retriable), instead of
retrying blindly or giving up too early.

## Development

```bash
pip install -e ".[dev]"
ruff format && ruff check && mypy
pytest --cov=sdmx_data_mcp --cov-branch --cov-report=term-missing
```

The suite holds 100% statement and branch coverage. Most server tests inject
a fake connector so every branch is reachable deterministically; a separate
end-to-end module drives the real `PandasConnector` against `respx`-mocked
responses, so drift in URL construction or SDMX-CSV parsing surfaces there.

## Relationship to pysdmx

This package depends on `pysdmx[data]` from PyPI and does not fork or vendor
it. The same server has also been proposed upstream as
[bis-med-it/pysdmx#669](https://github.com/bis-med-it/pysdmx/pull/669); this
package exists so it is installable today regardless of what happens there.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

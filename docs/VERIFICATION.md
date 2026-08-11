# M1 verification log

Everything here was produced by running [`scripts/verify_connector.py`](../scripts/verify_connector.py)
against the live BIS service on **11 August 2026** with **pysdmx 1.18.0**
(PyPI) and **fastmcp 3.4.7**.

Re-run the script before trusting any of it. The build brief's §7 rule
applies to this file too: trust the source over the notes.

## Confirmed as documented

| Claim | Result |
| --- | --- |
| `Endpoints` has exactly one member | `['BIS']` — confirmed, the cross-service loop has length 1 |
| `dataflows()` returns a sorted immutable tuple | `tuple`, 32 flows, sorted by agency/id/version |
| `dataflow()` accepts `"BIS:WS_CBS_PUB(1.0)"` shorthand | Confirmed |
| `dataflow(flow, filters)` scopes availability | `series_count` 228,370 → 6,671 under a 3-clause filter |
| `data()` returns a pandas DataFrame | Confirmed |
| Country codes hide in several dimensions | `CH` appears in `L_REP_CTY`, `CBS_BANK_TYPE`, **and** `L_CP_COUNTRY` |

## Contradicts or refines the brief

### 1. `obs_count` is `None` on BIS

The brief and BIS's own `SKILL.md` both present `obs_count` and
`series_count` as size signals to check before retrieval. On
`BIS:WS_CBS_PUB(1.0)`, `obs_count` is `None` — both for the full flow and
for a filtered subset. Only `series_count` is populated.

**Consequence:** the safety layer must treat `obs_count` as optional and
fall back to `series_count`. Code that does `if flow.obs_count > N` raises
`TypeError` against the one service the library ships with.

### 2. A "narrow" filter is still enormous

`L_MEASURE = 'S' AND L_REP_CTY = 'CH' AND FREQ = 'Q'` — three clauses,
one country — returns **478,965 rows**. The 6,671 remaining series each
carry ~70 quarterly observations.

**Consequence:** the row cap is load-bearing, not a nicety. `get_data`
caps rows and reports `truncated`.

### 3. Passing `columns` silently disables the index

`data(..., columns=["OBS_VALUE"])` returned columns
`['TIME_PERIOD', 'SERIES_KEY', 'OBS_VALUE']` with **no index set**
(`df.index.names == [None]`).

`PandasConnector.__get_columns` adds `SERIES_KEY`/`TIME_PERIOD` to a local
copy of the column set, but the later index step re-checks membership
against the *caller's* original `columns` argument. Since `SERIES_KEY` was
never in the caller's list, the index is skipped.

**Consequence:** harmless for us — the server flattens to records anyway —
but do not assume a `(SERIES_KEY, TIME_PERIOD)` MultiIndex exists when
`columns` was passed.

### 4. Server-side time pushdown works on BIS

`TIME_PERIOD >= '2020-Q1'` pushed down successfully: 478,965 → 112,648
rows. The fallback path is still implemented, because the brief's warning
concerns services generally, and BIS is only one of them. The fallback is
covered by tests rather than by live behaviour.

### 5. Reference target repo has moved

The brief cites `nescoffee-create/sdmx-mcp-gateway`. The live repository is
[`Baffelan/sdmx-mcp-gateway`](https://github.com/Baffelan/sdmx-mcp-gateway).
Its description confirms the gap this project fills: it "processes metadata
only, never handling bulk statistical data transfer."

## Raw output

```text
Endpoints members: ['BIS']

[1] dataflows() -> 32 flows, type=tuple
    BIS:BIS_REL_CAL(1.0) - BIS_RELEASE_CALENDAR
    BIS:WS_CBPOL(1.0) - Central bank policy rates
    BIS:WS_CBS_PUB(1.0) - Consolidated banking
    ...

[2] dataflow('BIS:WS_CBS_PUB(1.0)')
    name         = Consolidated banking
    obs_count    = None
    series_count = 228370
    dimensions   = 11

[3] dimensions whose availability contains 'CH':
      L_REP_CTY      (Reporting country)
      CBS_BANK_TYPE  (CBS bank type)
      L_CP_COUNTRY   (Counterparty country)

[4] dataflow(detail, "L_MEASURE = 'S' AND L_REP_CTY = 'CH' AND FREQ = 'Q'")
    series_count = 6671 (full: 228370)

[5] data(detail, ..., columns=['OBS_VALUE'])
    shape   = (478965, 3)
    columns = ['TIME_PERIOD', 'SERIES_KEY', 'OBS_VALUE']
    index   = [None]

[6] time pushdown OK -> shape=(112648, 3)

M1 PASSED
```

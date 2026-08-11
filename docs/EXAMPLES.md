# Worked examples

Real sessions against the BIS through `sdmx-data-mcp`. Every block below is
actual tool output.

---

## 1. Swiss policy rate since 2020

The full three-step flow: find, inspect, retrieve.

### Discovery

```text
search_dataflows(query="policy rate central bank")
```

```jsonc
{
  "service": "BIS",
  "search_terms": ["policy", "rate", "central", "bank"],
  "total_dataflows_on_service": 32,
  "match_count": 12,
  "dataflows": [
    {
      "ref": "BIS:WS_CBPOL(1.0)",
      "id": "WS_CBPOL",
      "name": "Central bank policy rates",
      "description": "The interest rate which best captures the monetary authorities' policy intentions.",
      "matched_on": "name"
    },
    {
      "ref": "BIS:WS_CBTA(1.0)",
      "name": "Central bank total assets",
      "description": "Tracks the evolution of the size of central bank balance sheets across the world.",
      "matched_on": "name"
    },
    {
      "ref": "BIS:WS_CPMI_MACRO(1.0)",
      "name": "CPMI macro",
      "matched_on": "description"
    }
    // ... 9 more
  ]
}
```

Note `matched_on`. `WS_CPMI_MACRO` matched on its *description*, not its name —
useful for judging how relevant a hit really is.

### Inspection

```text
inspect_dataflow(ref="BIS:WS_CBPOL(1.0)", find_code="CH")
```

```jsonc
{
  "name": "Central bank policy rates",
  "series_count": 98,
  "obs_count": null,
  "size_warning": null,
  "dimensions": [
    {
      "id": "FREQ", "name": "Frequency", "required": true, "code_count": 2,
      "codes": [{"id": "D", "name": "Daily"}, {"id": "M", "name": "Monthly"}],
      "codes_truncated": false
    },
    {
      "id": "REF_AREA", "name": "Reference area", "required": true,
      "code_count": 49,
      "codes": [
        {"id": "AR", "name": "Argentina"}, {"id": "AT", "name": "Austria"},
        {"id": "CH", "name": "Switzerland"}, {"id": "CN", "name": "China"}
        // ...
      ]
    }
  ],
  "code_locations": [
    {"component_id": "REF_AREA", "role_hint": "reference area",
     "code_id": "CH", "code_name": "Switzerland"}
  ]
}
```

`obs_count` is `null` — the BIS does not report it. `series_count` of 98 with
no `size_warning` means this is small enough to pull whole.

Exactly one `code_location`, so `CH` is unambiguous here. Contrast that with
[example 4](#4-an-ambiguous-country-code).

### Retrieval

```text
get_data(
  ref="BIS:WS_CBPOL(1.0)",
  filters="FREQ = 'M' AND REF_AREA = 'CH' AND TIME_PERIOD >= '2020-01'",
  columns=["OBS_VALUE"],
)
```

```jsonc
{
  "filter_applied": "FREQ = 'M' AND REF_AREA = 'CH' AND TIME_PERIOD >= '2020-01'",
  "filter_fallback": null,
  "columns": ["SERIES_KEY", "OBS_VALUE", "TIME_PERIOD"],
  "row_count": 79,
  "total_rows_available": 79,
  "truncated": false,
  "records": [
    {"SERIES_KEY": "M.CH", "OBS_VALUE": "-0.75", "TIME_PERIOD": "2020-01"},
    {"SERIES_KEY": "M.CH", "OBS_VALUE": "-0.75", "TIME_PERIOD": "2020-02"},
    {"SERIES_KEY": "M.CH", "OBS_VALUE": "-0.75", "TIME_PERIOD": "2020-03"}
    // ...
  ],
  "next_step": "Complete: all 79 matching rows were returned. Safe to aggregate."
}
```

The SNB's negative policy rate, straight out of the tool. `truncated: false`
and `row_count == total_rows_available`, so charting or averaging this is safe.

`filter_fallback` is `null`, meaning the BIS accepted the `TIME_PERIOD`
constraint server-side rather than the server having to filter locally.

---

## 2. Two currencies in one query

`OR` is not supported by the query parser. `IN (...)` is how you ask for
several values of one component.

```text
get_data(
  ref="BIS:WS_XRU(1.0)",
  filters="FREQ = 'M' AND CURRENCY IN ('CHF', 'KES') AND TIME_PERIOD >= '2026-01'",
  columns=["OBS_VALUE"],
)
```

```jsonc
{
  "row_count": 14,
  "total_rows_available": 14,
  "truncated": false,
  "records": [
    {"SERIES_KEY": "M.CH.CHF.E", "OBS_VALUE": "0.768269", "TIME_PERIOD": "2026-01"},
    {"SERIES_KEY": "M.CH.CHF.E", "OBS_VALUE": "0.771199", "TIME_PERIOD": "2026-02"},
    {"SERIES_KEY": "M.CH.CHF.E", "OBS_VALUE": "0.799617", "TIME_PERIOD": "2026-03"},
    {"SERIES_KEY": "M.CH.CHF.A", "OBS_VALUE": "0.790004", "TIME_PERIOD": "2026-01"},
    {"SERIES_KEY": "M.CH.CHF.A", "OBS_VALUE": "0.773047", "TIME_PERIOD": "2026-02"}
    // ...
  ]
}
```

Two collections come back per currency: `.E` (end of period) and `.A` (period
average). They answer different questions and should not be mixed.

A daily query works the same way:

```text
get_data(
  ref="BIS:WS_XRU(1.0)",
  filters="FREQ = 'D' AND CURRENCY IN ('CHF', 'KES') AND TIME_PERIOD >= '2026-07-25'",
  columns=["OBS_VALUE"],
)
```

```jsonc
{
  "row_count": 7, "total_rows_available": 7, "truncated": false,
  "records": [
    {"SERIES_KEY": "D.CH.CHF.A", "OBS_VALUE": "0.815173", "TIME_PERIOD": "2026-07-27"},
    {"SERIES_KEY": "D.CH.CHF.A", "OBS_VALUE": "0.819829", "TIME_PERIOD": "2026-07-28"},
    {"SERIES_KEY": "D.CH.CHF.A", "OBS_VALUE": "0.820035", "TIME_PERIOD": "2026-07-29"}
    // ...
  ]
}
```

Seven rows for a window that spans two currencies — all of them CHF. That
absence is the finding, and it sets up the next example.

---

## 3. A cross rate neither service publishes

Because both legs can actually be *retrieved*, an assistant can compute
something the BIS does not publish: a CHF/KES cross rate.

The interesting part is what it had to establish first.

```text
get_data(ref="BIS:WS_XRU(1.0)",
         filters="REF_AREA = 'KE' AND FREQ = 'M' AND TIME_PERIOD >= '2024-01'",
         columns=["OBS_VALUE"])
```

```jsonc
{
  "row_count": 48, "total_rows_available": 48, "truncated": false,
  "records": [
    {"SERIES_KEY": "M.KE.KES.A", "OBS_VALUE": "159.694032", "TIME_PERIOD": "2024-01"},
    {"SERIES_KEY": "M.KE.KES.A", "OBS_VALUE": "151.839943", "TIME_PERIOD": "2024-02"},
    {"SERIES_KEY": "M.KE.KES.A", "OBS_VALUE": "137.353665", "TIME_PERIOD": "2024-03"}
    // ... ends 2025-12
  ]
}
```

KES monthly data ends in **December 2025**, while CHF runs to mid-2026. There
is no daily KES series at all. So the finest frequency both currencies share is
monthly, and the most recent period they share is 2025-12.

Same-period USD rates (units of local currency per USD):

| Collection | CHF (`M.CH.CHF.*`) | KES (`M.KE.KES.*`) |
| --- | ---: | ---: |
| End of period (`E`) | 0.792681 | 129.0101 |
| Period average (`A`) | 0.797006 | 129.126615 |

Cross rate = KES per USD ÷ CHF per USD, keeping the collection consistent on
both legs:

| Basis | KES per CHF | CHF per KES |
| --- | ---: | ---: |
| End of period, 2025-12 | 162.7516 | 0.0061443 |
| Period average, 2025-12 | 162.0146 | 0.0061723 |

Two caveats that matter and that the tool output makes visible: this is a
computed cross, not a rate the BIS publishes, so it carries the rounding of
both legs; and it is pinned to the newest period the two currencies *share*,
not the newest period either one has.

---

## 4. An ambiguous country code

The case the server exists to prevent.

```text
inspect_dataflow(ref="BIS:WS_CBS_PUB(1.0)", find_code="CH")
```

```jsonc
{
  "series_count": 228370,
  "obs_count": null,
  "size_warning": "This scope holds 228,370 series. Each carries many observations, so get_data will almost certainly truncate at 1,000 rows. Add filters on the dimensions above before retrieving.",
  "code_locations": [
    {"component_id": "L_REP_CTY", "component_name": "Reporting country",
     "role_hint": "reporting country", "code_id": "CH"},
    {"component_id": "CBS_BANK_TYPE", "component_name": "CBS bank type",
     "role_hint": "bank type (shares a country codelist)", "code_id": "CH"},
    {"component_id": "L_CP_COUNTRY", "component_name": "Counterparty country",
     "role_hint": "counterparty country", "code_id": "CH"}
  ],
  "next_step": "That code is ambiguous - it appears in 3 components: L_REP_CTY (reporting country); CBS_BANK_TYPE (bank type (shares a country codelist)); L_CP_COUNTRY (counterparty country). Decide which role the question means, filter on that component, and state which one you used."
}
```

*"In Switzerland"* has three defensible readings here, and picking the wrong
one yields a confident, wrong number. The third is not even a country — the
bank-type dimension reuses the country codelist.

---

## 5. Errors that tell you what to do

Not every query succeeds. When one fails, the failure is classified.

```text
inspect_dataflow(ref="BIS:WS_XRU(1.0)",
                 filters="REF_AREA = 'KE' AND FREQ = 'D'")
```

```text
[internal_error] Unexpected message format - The payload could not be
deserialized. This likely indicates that the service did not respond with a
valid SDMX-JSON v2.0.0 response. | retriable=false | next_step: The service
failed, or returned a response that could not be parsed. Do not repeat the
identical call - narrow the filter or try a different dataflow, since the
fault is server-side.
```

Three things the assistant can act on immediately: the kind (`internal_error`,
not `not_found` — so the reference is fine), `retriable=false` (do not loop),
and a concrete next move.

This is a genuine BIS behaviour: asking for availability of a daily KES series
that does not exist returns a response that is not valid SDMX-JSON, rather than
an empty result or a clean 404.

---

## Screenshots

Client-side screenshots live in [`images/`](images/). See
[`images/README.md`](images/README.md) for what belongs there.

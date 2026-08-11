"""M1 verification: prove the pysdmx PandasConnector behaves as documented.

Run this before trusting anything in the MCP server. It exercises the exact
call sequence the server depends on, against the live BIS service.

Usage:
    python scripts/verify_connector.py
"""

import sys
import traceback

from pysdmx.api.dc import Endpoints
from pysdmx.api.dc.pd import PandasConnector


def main() -> int:
    """Run the M1 checks and report pass/fail per step."""
    print(f"Endpoints members: {[e.name for e in Endpoints]}")
    conn = PandasConnector(Endpoints.BIS, timeout=60.0)

    # --- Step 1: discovery -------------------------------------------------
    flows = conn.dataflows()
    print(f"\n[1] dataflows() -> {len(flows)} flows, type={type(flows).__name__}")
    for f in flows[:8]:
        print(f"    {f.agency}:{f.id}({f.version}) - {f.name}")

    # --- Step 2: inspection ------------------------------------------------
    target = next(f for f in flows if f.id == "WS_CBS_PUB")
    detail = conn.dataflow(f"{target.agency}:{target.id}({target.version})")
    print(f"\n[2] dataflow('{target.agency}:{target.id}({target.version})')")
    print(f"    name        = {detail.name}")
    print(f"    obs_count   = {detail.obs_count}")
    print(f"    series_count= {detail.series_count}")

    dims = list(detail.components.dimensions)
    print(f"    dimensions  = {len(dims)}")
    for d in dims:
        codes = [c.id for c in (d.enumeration or [])]
        preview = ",".join(codes[:6])
        print(f"      {d.id}: {len(codes)} codes [{preview}...]")

    # --- Step 3: which dimensions carry a country code? --------------------
    print("\n[3] dimensions whose availability contains 'CH':")
    for d in dims:
        codes = {c.id for c in (d.enumeration or [])}
        if "CH" in codes:
            print(f"      {d.id}  ({d.name})")

    # --- Step 4: scoped availability ---------------------------------------
    flt = "L_MEASURE = 'S' AND L_REP_CTY = 'CH' AND FREQ = 'Q'"
    scoped = conn.dataflow(detail, flt)
    print(f"\n[4] dataflow(detail, {flt!r})")
    print(f"    obs_count   = {scoped.obs_count} (full: {detail.obs_count})")
    print(f"    series_count= {scoped.series_count} (full: {detail.series_count})")

    # --- Step 5: actually fetch observations -------------------------------
    df = conn.data(detail, flt, columns=["OBS_VALUE"])
    print(f"\n[5] data(detail, {flt!r}, columns=['OBS_VALUE'])")
    print(f"    shape   = {df.shape}")
    print(f"    columns = {list(df.columns)}")
    print(f"    index   = {df.index.names}")
    print(df.head(5).to_string())

    # --- Step 6: does server-side time pushdown work? ----------------------
    tflt = flt + " AND TIME_PERIOD >= '2020-Q1'"
    try:
        tdf = conn.data(detail, tflt, columns=["OBS_VALUE"])
        print(f"\n[6] time pushdown OK -> shape={tdf.shape}")
    except Exception as e:  # noqa: BLE001 - probing behaviour on purpose
        print(f"\n[6] time pushdown FAILED -> {type(e).__name__}: {e}")

    print("\nM1 PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        print("\nM1 FAILED")
        sys.exit(1)

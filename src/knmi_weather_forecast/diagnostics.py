"""
Diagnostics for KNMI data coverage per station and variable.

Used to flag stations that don't reliably measure a given variable
(e.g. tide/water-level gauges that report wind but not temperature),
since the models were never trained on meaningful data for those
station/variable combinations.
"""

from __future__ import annotations

import pandas as pd

from knmi_weather_forecast.config import (
    COVERAGE_THRESHOLD,
    STATION_COVERAGE_PATH,
    TARGET_VAR_RAW_CODES,
    TRAIN_START_DATE,
)

RAW_VARIABLE_CODES = list(TARGET_VAR_RAW_CODES.values())


def compute_variable_coverage(
    raw_df: pd.DataFrame, variables: list[str] | None = None
) -> pd.DataFrame:
    """
    For each station, compute the fraction of non-missing days for each
    of the given raw KNMI columns (pre-rename, e.g. 'TG', 'RH', 'FG').
    """
    if variables is None:
        variables = RAW_VARIABLE_CODES

    rows = []
    for station, group in raw_df.groupby("STN"):
        row = {"station": station, "total_days": len(group)}
        for var in variables:
            if var in group.columns:
                row[f"{var}_coverage"] = group[var].notna().mean()
            else:
                row[f"{var}_coverage"] = 0.0
        rows.append(row)

    return pd.DataFrame(rows)


def get_unreliable_stations(
    coverage_df: pd.DataFrame,
    variables: list[str] | None = None,
    threshold: float = COVERAGE_THRESHOLD,
) -> dict[str, set[int]]:
    """
    Returns {raw_var_code: set(station_ids)} for stations below the
    coverage threshold for that variable.
    """
    if variables is None:
        variables = RAW_VARIABLE_CODES

    unreliable = {}
    for var in variables:
        col = f"{var}_coverage"
        if col not in coverage_df.columns:
            continue
        low = coverage_df[coverage_df[col] < threshold]
        unreliable[var] = set(low["station"])

    return unreliable


if __name__ == "__main__":
    from knmi_weather_forecast.data import load_or_fetch_daily_data

    raw = load_or_fetch_daily_data(start=TRAIN_START_DATE)
    coverage = compute_variable_coverage(raw)

    pd.set_option("display.max_rows", None)
    print(coverage.sort_values(f"{RAW_VARIABLE_CODES[0]}_coverage"))

    unreliable = get_unreliable_stations(coverage)
    for var, stations in unreliable.items():
        print(f"\nStations with <{COVERAGE_THRESHOLD:.0%} coverage for {var}:")
        print(sorted(stations))

    STATION_COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(STATION_COVERAGE_PATH, index=False)
    print(f"\nSaved coverage table to {STATION_COVERAGE_PATH}")
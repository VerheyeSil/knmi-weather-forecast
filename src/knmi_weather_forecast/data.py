"""
Download and load KNMI daily weather data (Daggegevens) for all stations.

Data source: https://www.daggegevens.knmi.nl/klimatologie/daggegevens
No API key required. Docs (Dutch): https://www.knmi.nl/kennis-en-datacentrum/achtergrond/data-ophalen-vanuit-een-script
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

from knmi_weather_forecast.config import (
    DAILY_CACHE_PATH,
    DEFAULT_FETCH_START,
    FETCH_CHUNK_DAYS,
    KNMI_DAILY_URL,
    RAW_DATA_DIR,
    STATION_METADATA_PROBE_DATE,
)


def fetch_daily_data(
    stations: str = "ALL",
    start: str = DEFAULT_FETCH_START,
    end: str | None = None,
    variables: str = "ALL",
    save_raw: bool = True,
) -> pd.DataFrame:
    """
    Fetch daily weather data from KNMI for the given stations and date range.

    Parameters
    ----------
    stations : str
        "ALL" for every station, or a colon-separated list of station numbers,
        e.g. "260:240:280".
    start : str
        Start date in YYYYMMDD format.
    end : str | None
        End date in YYYYMMDD format. Defaults to yesterday if not given.
    variables : str
        "ALL" for every variable, or a colon-separated list, e.g. "TEMP:PRCP:WIND".
    save_raw : bool
        If True, saves the raw response text to data/raw/ before parsing.

    Returns
    -------
    pd.DataFrame
        Parsed daily observations, one row per station per day.
    """
    if end is None:
        end = (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y%m%d")

    payload = {
        "stns": stations,
        "start": start,
        "end": end,
        "vars": variables,
    }

    response = requests.post(KNMI_DAILY_URL, data=payload, timeout=60)
    response.raise_for_status()

    raw_text = response.text

    if save_raw:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = RAW_DATA_DIR / f"daily_{stations}_{start}_{end}.txt"
        raw_path.write_text(raw_text, encoding="utf-8")

    return _parse_daily_response(raw_text)


def _parse_daily_response(raw_text: str) -> pd.DataFrame:
    """
    Parse KNMI's daily data response.

    The response is a mix of comment lines (starting with '#', containing
    disclaimers, station metadata, and variable descriptions) and a CSV body.
    The column header itself is also prefixed with '# '.
    """
    lines = raw_text.splitlines()

    header_line = None
    data_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if stripped.replace("#", "").strip().startswith("STN"):
                header_line = stripped.lstrip("#").strip()
        else:
            data_lines.append(stripped)

    if header_line is None:
        raise ValueError(
            "Could not find header row in KNMI response. "
            "This can happen if the query returned an error page instead "
            "of data (e.g. KNMI's 'too many results' error for very large "
            "requests) — inspect the raw response text."
        )

    columns = [c.strip() for c in header_line.split(",")]
    csv_body = "\n".join(data_lines)

    df = pd.read_csv(
        io.StringIO(csv_body),
        names=columns,
        skipinitialspace=True,
    )

    df.columns = [c.strip() for c in df.columns]

    # Force proper numeric dtypes. Very recent days can have sparse or
    # oddly-whitespaced fields (data not yet finalized by KNMI), which
    # pandas can misread as object dtype instead of numeric-with-NaN. If
    # that ever slips through uncorrected and gets concatenated with
    # properly-typed cached data, pandas upcasts the whole column to
    # object to reconcile the mismatch — silently breaking every
    # downstream numeric check. Coercing here, on every parse, prevents
    # that regardless of how a given day's raw text happens to look.
    for col in df.columns:
        if col in ("date",):
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "YYYYMMDD" in df.columns:
        df["date"] = pd.to_datetime(df["YYYYMMDD"], format="%Y%m%d")

    return df


def fetch_daily_data_long_range(
    start: str,
    end: str | None = None,
    stations: str = "ALL",
    variables: str = "ALL",
    chunk_days: int = FETCH_CHUNK_DAYS,
) -> pd.DataFrame:
    """
    Same as fetch_daily_data, but for long date ranges that would otherwise
    trigger KNMI's "too many results" error when requesting ALL stations
    and ALL variables at once. Splits the range into smaller chunks,
    fetches each separately, and concatenates the results.
    """
    if end is None:
        end = (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y%m%d")

    start_date = pd.to_datetime(start, format="%Y%m%d")
    end_date = pd.to_datetime(end, format="%Y%m%d")

    chunks = []
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + pd.Timedelta(days=chunk_days), end_date)

        print(f"Fetching {chunk_start.date()} to {chunk_end.date()}...")
        chunk_df = fetch_daily_data(
            stations=stations,
            start=chunk_start.strftime("%Y%m%d"),
            end=chunk_end.strftime("%Y%m%d"),
            variables=variables,
            save_raw=False,
        )
        chunks.append(chunk_df)

        chunk_start = chunk_end + pd.Timedelta(days=1)

    return pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["STN", "YYYYMMDD"])


def load_or_fetch_daily_data(
    start: str,
    end: str | None = None,
    stations: str = "ALL",
    variables: str = "ALL",
    cache_path: Path = DAILY_CACHE_PATH,
) -> pd.DataFrame:
    """
    Local-cache-aware version of fetch_daily_data_long_range.

    On first call, fetches the full requested range from KNMI and saves it
    to a local parquet cache. On later calls, only fetches whatever date
    range is missing from the cache (e.g. new recent days, or an earlier
    range if you extend `start` further back) and merges it in.

    Note: assumes stations="ALL" and variables="ALL" stay constant across
    calls. If you ever narrow either, delete the cache file and refetch.
    """
    if end is None:
        end = (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y%m%d")

    requested_start = pd.to_datetime(start, format="%Y%m%d")
    requested_end = pd.to_datetime(end, format="%Y%m%d")

    if cache_path.exists():
        cached = pd.read_parquet(cache_path)
        cached_dates = pd.to_datetime(cached["YYYYMMDD"], format="%Y%m%d")
        cached_min, cached_max = cached_dates.min(), cached_dates.max()
    else:
        cached = pd.DataFrame()
        cached_min, cached_max = None, None

    missing_ranges = []
    if cached.empty:
        missing_ranges.append((requested_start, requested_end))
    else:
        if requested_start < cached_min:
            missing_ranges.append((requested_start, cached_min - pd.Timedelta(days=1)))
        if requested_end > cached_max:
            missing_ranges.append((cached_max + pd.Timedelta(days=1), requested_end))

    new_chunks = []
    for range_start, range_end in missing_ranges:
        print(f"Cache miss: fetching {range_start.date()} to {range_end.date()} from KNMI...")
        new_chunks.append(
            fetch_daily_data_long_range(
                start=range_start.strftime("%Y%m%d"),
                end=range_end.strftime("%Y%m%d"),
                stations=stations,
                variables=variables,
            )
        )

    if new_chunks:
        combined = pd.concat([cached, *new_chunks], ignore_index=True)
        combined = combined.drop_duplicates(subset=["STN", "YYYYMMDD"]).sort_values(
            ["STN", "YYYYMMDD"]
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(cache_path, index=False)
        print(f"Cache updated: {len(combined)} total rows saved to {cache_path}")
    else:
        combined = cached
        print(f"Using cached data ({len(combined)} rows) — nothing new to fetch.")

    dates = pd.to_datetime(combined["YYYYMMDD"], format="%Y%m%d")
    mask = (dates >= requested_start) & (dates <= requested_end)
    result = combined[mask].reset_index(drop=True)

    if "date" not in result.columns:
        result["date"] = pd.to_datetime(result["YYYYMMDD"], format="%Y%m%d")

    return result


def fetch_station_metadata() -> pd.DataFrame:
    """
    Fetch KNMI's station metadata (number, lon, lat, altitude, name) by
    parsing the header block that comes with every daily-data response.
    This avoids hardcoding a station list that could drift out of date.

    The block looks like:
        # STN         LON(east)   LAT(north)  ALT(m)      NAME
        # 209         4.518       52.465      0.00        IJmond
        # 210         4.430       52.171      -0.20       VALKENBURG VK
        ...
    and is followed by variable descriptions like "# TG        : ...",
    which is how we know the station block has ended.
    """
    response = requests.post(
        KNMI_DAILY_URL,
        data={
            "stns": "ALL",
            "start": STATION_METADATA_PROBE_DATE,
            "end": STATION_METADATA_PROBE_DATE,
            "vars": "TG",
        },
        timeout=60,
    )
    response.raise_for_status()

    lines = response.text.splitlines()
    station_rows = []
    in_station_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        content = stripped.lstrip("#").strip()

        if content.startswith("STN") and "LON" in content:
            in_station_block = True
            continue

        if not in_station_block:
            continue

        parts = content.split()
        if len(parts) < 4:
            continue

        station_token, lon_token, lat_token, alt_token = parts[:4]
        if not station_token.isdigit():
            break

        try:
            station_id = int(station_token)
            lon = float(lon_token)
            lat = float(lat_token)
            alt = float(alt_token)
        except ValueError:
            break

        name = " ".join(parts[4:]).strip()
        station_rows.append(
            {"station": station_id, "lon": lon, "lat": lat, "alt_m": alt, "name": name}
        )

    if not station_rows:
        raise ValueError(
            "Could not parse station metadata from KNMI response. "
            "The response format may have changed — inspect the raw text."
        )

    return pd.DataFrame(station_rows)


if __name__ == "__main__":
    # Quick manual test: pull the last 30 days for all stations
    df = fetch_daily_data(start=(pd.Timestamp.today() - pd.Timedelta(days=30)).strftime("%Y%m%d"))
    print(df.shape)
    print(df.head())
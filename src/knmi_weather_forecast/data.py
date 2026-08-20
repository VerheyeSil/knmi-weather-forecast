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

KNMI_DAILY_URL = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def fetch_daily_data(
    stations: str = "ALL",
    start: str = "20200101",
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
            # The header row is the last comment line that starts with "# STN"
            if stripped.replace("#", "").strip().startswith("STN"):
                header_line = stripped.lstrip("#").strip()
        else:
            data_lines.append(stripped)

    if header_line is None:
        raise ValueError(
            "Could not find header row in KNMI response. "
            "The response format may have changed — inspect the raw text."
        )

    columns = [c.strip() for c in header_line.split(",")]
    csv_body = "\n".join(data_lines)

    df = pd.read_csv(
        io.StringIO(csv_body),
        names=columns,
        skipinitialspace=True,
    )

    # Clean up column names (KNMI sometimes leaves stray whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Parse date column (YYYYMMDD -> datetime)
    if "YYYYMMDD" in df.columns:
        df["date"] = pd.to_datetime(df["YYYYMMDD"], format="%Y%m%d")

    return df


if __name__ == "__main__":
    # Quick manual test: pull the last 30 days for all stations
    df = fetch_daily_data(start=(pd.Timestamp.today() - pd.Timedelta(days=30)).strftime("%Y%m%d"))
    print(df.shape)
    print(df.head())
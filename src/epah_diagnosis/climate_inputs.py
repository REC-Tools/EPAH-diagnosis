"""Strict temporal and unit checks shared by the ERA5 climate prototypes."""
from __future__ import annotations

import pandas as pd
import numpy as np


def temperature_offset(units: object) -> float:
    """Convert explicit CF temperature units to Celsius; never guess by value."""
    name = str(units or "").strip().casefold().replace(" ", "")
    if name in {"k", "kelvin", "degree_kelvin", "degrees_kelvin"}:
        return -273.15
    if name in {"c", "°c", "degc", "celsius", "degree_celsius", "degrees_celsius",
                "degreecelsius", "degreescelsius", "degree_c", "degrees_c"}:
        return 0.0
    raise ValueError(f"Explicit Kelvin or Celsius temperature units required; got {units!r}")


def annual_time_indices(dataset, axis: str, year: int, *, hourly: bool = False) -> list[int]:
    """Select a complete Gregorian year of unique midnight days or UTC hours."""
    if not isinstance(year, int) or not 1900 <= year <= 2100:
        raise ValueError("Reference year must be between 1900 and 2100")
    if axis not in dataset.coords or dataset[axis].dims != (axis,):
        raise ValueError("Expected a one-dimensional decoded time coordinate")
    index = dataset[axis].to_index()
    if not isinstance(index, pd.DatetimeIndex) or index.hasnans or index.tz is not None:
        raise ValueError("Expected a decoded Gregorian time coordinate without missing timestamps")
    selected = [i for i, stamp in enumerate(index) if stamp.year == year]
    actual = index[selected]
    if actual.has_duplicates:
        raise ValueError(f"Duplicate timestamps in reference year {year}")
    expected = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01",
                             freq="h" if hourly else "D", inclusive="left")
    if len(actual) != len(expected) or set(actual) != set(expected):
        frequency = "hourly" if hourly else "daily"
        raise ValueError(f"Incomplete or irregular {frequency} calendar for {year}: "
                         f"expected {len(expected)} timestamps, found {len(actual)}")
    return sorted(selected, key=lambda i: index[i])


def municipal_mean(variable, time_axis: str, lat_axis: str, lon_axis: str,
                   time_indices: list[int], cells: list[tuple[int, int]],
                   offset: float, municipality: str) -> list[float]:
    """Read each selected cell once, retaining a fixed denominator for the year."""
    series = [np.asarray(variable.isel({time_axis: time_indices, lat_axis: row,
                                       lon_axis: col}).values, dtype=float)
              for row, col in cells]
    values = np.stack(series)
    if not np.isfinite(values).all():
        raise ValueError(f"Missing/nonfinite temperature observation for {municipality}")
    return (values.mean(axis=0) + offset).tolist()

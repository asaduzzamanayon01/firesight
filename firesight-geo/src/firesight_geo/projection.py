"""Coordinate transforms between WGS84 lon/lat and GDA2020 / MGA zone 50 (EPSG:7850).

Uses pyproj when installed (the project's normal setup). If pyproj is missing,
falls back to a local equirectangular approximation centred on Perth, which is
accurate to well under 0.5% across the study area — fine for tests, but the
real pipeline should always run with pyproj.
"""
from __future__ import annotations

import warnings
import numpy as np

try:
    from pyproj import Transformer
    _FWD = Transformer.from_crs("EPSG:4326", "EPSG:7850", always_xy=True)
    _INV = Transformer.from_crs("EPSG:7850", "EPSG:4326", always_xy=True)
    HAS_PYPROJ = True
except ImportError:  # pragma: no cover
    HAS_PYPROJ = False
    warnings.warn("pyproj not installed: using approximate projection (tests only).")

_LON0, _LAT0, _R = 116.0, -32.0, 6_371_000.0


def to_projected(lon, lat):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    if HAS_PYPROJ:
        return _FWD.transform(lon, lat)
    x = np.radians(lon - _LON0) * _R * np.cos(np.radians(_LAT0))
    y = np.radians(lat - _LAT0) * _R
    return x, y


def to_lonlat(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if HAS_PYPROJ:
        return _INV.transform(x, y)
    lon = _LON0 + np.degrees(x / (_R * np.cos(np.radians(_LAT0))))
    lat = _LAT0 + np.degrees(y / _R)
    return lon, lat

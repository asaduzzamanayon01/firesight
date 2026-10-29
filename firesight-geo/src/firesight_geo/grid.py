"""3 km analysis grid for the Perth metropolitan area and Darling Scarp.

Cells are built in a projected CRS (GDA2020 / MGA zone 50, EPSG:7850) so every
cell is a true 3 km x 3 km square. Each cell gets a stable integer `cell_id`
and a row/column index, which the label and split modules use.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .projection import to_lonlat, to_projected

# Study area (lon/lat, WGS84). Adjust here if the team agrees a different extent.
STUDY_BBOX = {"min_lon": 115.65, "max_lon": 116.30, "min_lat": -32.60, "max_lat": -31.60}
CELL_SIZE_M = 3000.0


def build_grid(bbox: dict = STUDY_BBOX, cell_size_m: float = CELL_SIZE_M) -> pd.DataFrame:
    """Return one row per grid cell with its id, row/col, bounds and centroid."""
    xs, ys = to_projected(
        np.array([bbox["min_lon"], bbox["max_lon"], bbox["min_lon"], bbox["max_lon"]]),
        np.array([bbox["min_lat"], bbox["min_lat"], bbox["max_lat"], bbox["max_lat"]]),
    )
    # Snap the origin to a multiple of the cell size so the grid is reproducible.
    x0 = np.floor(xs.min() / cell_size_m) * cell_size_m
    y0 = np.floor(ys.min() / cell_size_m) * cell_size_m
    n_cols = int(np.ceil((xs.max() - x0) / cell_size_m))
    n_rows = int(np.ceil((ys.max() - y0) / cell_size_m))

    rows, cols = np.meshgrid(np.arange(n_rows), np.arange(n_cols), indexing="ij")
    rows, cols = rows.ravel(), cols.ravel()
    minx = x0 + cols * cell_size_m
    miny = y0 + rows * cell_size_m
    cx, cy = minx + cell_size_m / 2, miny + cell_size_m / 2
    clon, clat = to_lonlat(cx, cy)

    grid = pd.DataFrame({
        "cell_id": rows * n_cols + cols,
        "row": rows, "col": cols,
        "minx": minx, "miny": miny, "maxx": minx + cell_size_m, "maxy": miny + cell_size_m,
        "centroid_x": cx, "centroid_y": cy, "centroid_lon": clon, "centroid_lat": clat,
    })
    grid.attrs.update({"x0": x0, "y0": y0, "n_rows": n_rows, "n_cols": n_cols,
                       "cell_size_m": cell_size_m})
    return grid


def assign_cells(lon, lat, grid: pd.DataFrame) -> np.ndarray:
    """Map lon/lat points to cell_id. Points outside the grid get -1."""
    x, y = to_projected(np.asarray(lon, float), np.asarray(lat, float))
    a = grid.attrs
    col = np.floor((x - a["x0"]) / a["cell_size_m"]).astype(int)
    row = np.floor((y - a["y0"]) / a["cell_size_m"]).astype(int)
    inside = (col >= 0) & (col < a["n_cols"]) & (row >= 0) & (row < a["n_rows"])
    return np.where(inside, row * a["n_cols"] + col, -1)


def save_grid(grid: pd.DataFrame, path: str) -> None:
    """Save as GeoPackage when geopandas is installed, otherwise CSV."""
    try:
        import geopandas as gpd
        from shapely.geometry import box
        geom = [box(r.minx, r.miny, r.maxx, r.maxy) for r in grid.itertuples()]
        gpd.GeoDataFrame(grid, geometry=geom, crs="EPSG:7850").to_file(path, driver="GPKG")
    except ImportError:
        grid.to_csv(path.rsplit(".", 1)[0] + ".csv", index=False)

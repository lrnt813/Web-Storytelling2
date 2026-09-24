"""ID grid asli (Langkah 1 putaran 2)."""
import geopandas as gpd
import numpy as np
from shapely.geometry import box

from backend.engine import original_grid_ids


def _grid(ids):
    geoms = [box(x * 100, 0, x * 100 + 100, 100) for x in range(len(ids))]
    return gpd.GeoDataFrame({"Id": ids}, geometry=geoms, crs="EPSG:32749")


def test_pakai_kolom_id_bila_unik():
    assert list(original_grid_ids(_grid([5, 7, 11]))) == ["5", "7", "11"]


def test_fallback_centroid_bila_tidak_unik():
    ids = original_grid_ids(_grid([1, 1, 2]))
    assert list(ids) == ["E50_N50", "E150_N50", "E250_N50"]


def test_fallback_centroid_bila_ada_null():
    ids = original_grid_ids(_grid([1.0, np.nan, 3.0]))
    assert ids[0].startswith("E") and len(set(ids)) == 3

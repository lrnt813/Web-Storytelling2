"""Kelas bahaya dari satu raster InaRisk (Putaran 3, Langkah 1 — keputusan peneliti)."""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString, Point, box

from backend.hazard_raster import HazardRaster

DATA = Path(__file__).resolve().parents[1] / "data"


def _raster(a):
    """HazardRaster sintetis: piksel 10 m, pojok kiri atas (0, 100)."""
    r = HazardRaster.__new__(HazardRaster)
    r.a = np.asarray(a, dtype=np.int8)
    r.transform = Affine(10.0, 0, 0, 0, -10.0, 100.0)
    return r


def test_grid_mayoritas_seri_ke_kelas_terendah_dan_titik():
    a = np.zeros((10, 10), int)
    a[0:2, 0:2] = [[3, 3], [3, 0]]      # sel kiri atas 20×20 m: 3 piksel kelas 3, 1 piksel kelas 0
    a[0:2, 2:4] = [[2, 2], [1, 1]]      # seri 2 vs 1 → 1
    r = _raster(a)
    g = gpd.GeoDataFrame(geometry=[box(0, 80, 20, 100), box(20, 80, 40, 100), box(40, 80, 60, 100)])
    assert r.grid_majority(g).tolist() == [3, 1, 0]
    assert r.points([Point(5, 95), Point(35, 85), Point(500, 500)]).tolist() == [3, 1, 0]


def test_ruas_maksimum_sepanjang_garis():
    a = np.zeros((10, 10), int)
    a[5, 7] = 3                         # satu piksel kelas 3 di x 70–80, y 40–50
    a[5, 2] = 1
    r = _raster(a)
    lines = [LineString([(0, 45), (100, 45)]), LineString([(0, 15), (100, 15)]), LineString([(21, 44), (29, 44)])]
    assert r.line_max(lines).tolist() == [3, 0, 1]


@pytest.mark.skipif(not (DATA / "Kulonprogo_Banjir.tif").exists(), reason="raster tidak tersedia")
def test_data_asli_tes_sama_dengan_atribut_lama():
    """Atribut kelas TES lama identik dengan nilai piksel raster di titik TES (asal-usul sama)."""
    from backend.engine import Cfg, _read_gpkg
    cfg = Cfg(base_dir=str(DATA))
    r = HazardRaster(str(DATA / "Kulonprogo_Banjir.tif"))
    for kat, fp in cfg.tes_files.items():
        t = _read_gpkg(fp, cfg.target_crs, ["Point"])
        assert np.array_equal(r.points(t.geometry.values), t["banjir"].values), kat

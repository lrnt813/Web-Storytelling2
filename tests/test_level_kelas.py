"""Level berbasis kelas bahaya (Langkah 2 putaran 2).

Untuk setiap level, himpunan grid tergenang (simulate_hazard) dan ruas yang ditutup
(build_road_graph / road_closed_mask) harus sama persis dengan aturan kelas:
Baseline = tidak ada, Rendah = kelas 3, Sedang = kelas ≥ 2, Tinggi = kelas ≥ 1.
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString

from backend import thesis as T
from backend.engine import Cfg, build_road_graph, road_closed_mask, simulate_hazard

DATA = Path(__file__).resolve().parents[1] / "data"
ATURAN = {"baseline": [], "rendah": [3], "sedang": [2, 3], "tinggi": [1, 2, 3]}


def test_definisi_level():
    assert {lv["key"]: lv["kelas_ditutup"] for lv in T.LEVELS} == ATURAN
    assert T.LEVEL_BY_KEY["rendah"]["label_lengkap"] == "Level Rendah (kelas 3 ditutup)"


def test_graf_jalan_sintetis_menutup_kelas_yang_benar():
    cfg = Cfg(base_dir=str(DATA))
    roads = gpd.GeoDataFrame({"banjir": [0, 1, 2, 3]},
                             geometry=[LineString([(i * 10, 0), (i * 10, 5)]) for i in range(4)],
                             crs=cfg.target_crs)
    for lv in T.LEVELS:
        G, _, _ = build_road_graph(roads, T.SKENARIO, lv["intensity"], cfg)
        tersisa = sorted(int(u[0] // 10) for u, v in G.edges())
        assert tersisa == [c for c in range(4) if c not in lv["kelas_ditutup"]], lv["key"]


@pytest.fixture(scope="module")
def data():
    if not (DATA / "Kulonprogo_Ready4.gpkg").exists():
        pytest.skip("data GPKG tidak tersedia")
    from backend.engine import load_data, load_road_network
    cfg = Cfg(base_dir=str(DATA))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    return cfg, gdf, roads, tes


@pytest.mark.parametrize("key", list(ATURAN))
def test_himpunan_grid_dan_ruas_sama_dengan_aturan_kelas(data, key):
    cfg, gdf, roads, tes = data
    lv = T.LEVEL_BY_KEY[key]
    _, _, _, mask = simulate_hazard(gdf, roads, tes, T.SKENARIO, lv["intensity"], cfg)
    assert np.array_equal(mask, T.grid_class_rule_mask(gdf, lv))
    closed = road_closed_mask(roads, T.SKENARIO, lv["intensity"], cfg)
    assert np.array_equal(closed, T.road_class_rule_mask(roads, lv))

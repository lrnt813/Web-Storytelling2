"""Waktu tempuh memuat ruas snapping (Langkah 3 putaran 2)."""
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pytest
from scipy.spatial import cKDTree
from shapely.geometry import Point

from backend.engine import Cfg, compute_distances
from backend.thesis import detect_tas_detour

DATA = Path(__file__).resolve().parents[1] / "data"


def _jalan():
    G = nx.Graph()
    xs = np.arange(0, 2001, 100.0)
    for a, b in zip(xs[:-1], xs[1:]):
        G.add_edge((a, 0.0), (b, 0.0), weight=100.0)
    nl = np.array(list(G.nodes()))
    return G, nl, cKDTree(nl)


def test_waktu_tes_memuat_ruas_snapping_grid_dan_tes():
    G, nl, tn = _jalan()
    cfg = Cfg()
    grid = pd.DataFrame({"cx": [0.0, 500.0, 1000.0, 5000.0], "cy": [20.0, 40.0, 10.0, 5000.0]})
    tes = gpd.GeoDataFrame({"kategori": ["ibadah", "ibadah"]},
                           geometry=[Point(1000.0, 30.0), Point(1900.0, -250.0)], crs=cfg.target_crs)
    tpk, tm, _, _, opsi = compute_distances(grid, "banjir", tes, cfg, 0.0, 400.0, None, None, G, nl, tn)
    v = cfg.walking_speed_m_per_min
    expect = np.array([20 + 1000 + 30, 40 + 500 + 30, 10 + 0 + 30]) / v
    assert np.allclose(tpk["ibadah"][:3], expect)
    assert tpk["ibadah"][3] == 400.0                     # gagal snapping (> 300 m) -> penalti
    assert np.all(tpk["pendidikan"] == 400.0)             # kategori tanpa TES -> penalti
    assert list(opsi) == [1, 1, 1, 0]


def test_t_aktual_memuat_ruas_snapping_dan_tidak_lebih_kecil_dari_euclid():
    G, nl, tn = _jalan()
    cfg = Cfg()
    grid_xy = np.array([[x, 20.0] for x in range(0, 2001, 100)] + [[1000.0, 60.0]], float)
    tes = gpd.GeoDataFrame({"kategori": ["ibadah"]}, geometry=[Point(1000.0, 30.0)], crs=cfg.target_crs)
    res = detect_tas_detour(pd.DataFrame(index=range(len(grid_xy))), grid_xy, tes, (G, nl, tn), 400.0, cfg)
    v = cfg.walking_speed_m_per_min
    assert np.isclose(res["t_aktual"][0], (20 + 1000 + 30) / v)
    reach = res["status"] != 2
    assert np.all(res["t_aktual"][reach] >= res["t_euclid_raw"][reach] - 1e-9)


@pytest.mark.skipif(not (DATA / "Kulonprogo_Ready4.gpkg").exists(), reason="data tidak tersedia")
def test_data_asli_t_aktual_tidak_lebih_kecil_dari_t_ideal():
    """Baseline data asli: untuk grid terjangkau T_aktual ≥ T_ideal (toleransi numerik)."""
    from backend import thesis as T
    from backend.engine import load_data, load_road_network
    cfg = Cfg(base_dir=str(DATA))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    acc = T.compute_level_accessibility(gdf, roads, tes, 0.0, cfg)
    xy = np.column_stack([gdf["cx"].values, gdf["cy"].values])
    res = detect_tas_detour(acc["df"], xy, acc["tes_v"], acc["graph"], acc["t_pen"], cfg)
    reach = res["status"] != 2
    assert np.all(res["t_aktual"][reach] >= res["t_euclid_raw"][reach] - 1e-9)
    assert np.all(res["t_aktual"][reach] >= res["t_ideal"][reach] - 1e-9), \
        f"{res['summary']['jumlah_t_aktual_lt_t_ideal']} grid dengan T_aktual < T_ideal"

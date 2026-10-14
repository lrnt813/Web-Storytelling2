"""Simulasi blokir jalan dashboard: titik blokir hanya boleh pada jaringan jalan."""
import geopandas as gpd
import networkx as nx
import numpy as np
from shapely.geometry import LineString

from backend.engine import Cfg, apply_road_cuts_to_graph, build_road_graph
from backend.road_cut import CUT_TOL_MAX_M, RoadIndex


def _roads():
    return gpd.GeoDataFrame({"banjir": [0, 0, 0]},
                            geometry=[LineString([(0, 0), (100, 0)]), LineString([(100, 0), (200, 0)]),
                                      LineString([(100, 0), (100, 100)])], crs="EPSG:32749")


def test_klik_di_dekat_ruas_ditempel_ke_ruas_terdekat():
    s = RoadIndex(_roads()).snap(150, 8, tol_m=20)
    assert s["id_jalan"] == 1 and np.isclose(s["jarak_m"], 8) and np.isclose(s["y"], 0) and np.isclose(s["x"], 150)
    assert s["edge_from"] == [100.0, 0.0] and s["edge_to"] == [200.0, 0.0]


def test_klik_di_luar_jaringan_jalan_ditolak():
    idx = RoadIndex(_roads())
    assert idx.snap(150, 40, tol_m=20) is None                    # 40 m dari jalan terdekat
    assert idx.snap(300, 90, tol_m=500) is None                   # 134 m; toleransi dibatasi CUT_TOL_MAX_M
    assert CUT_TOL_MAX_M < 134


def test_blokir_hanya_memutus_ruas_yang_diklik():
    roads = _roads()
    G, nl, tn = build_road_graph(roads, "banjir", 0.0, Cfg())
    s = RoadIndex(roads).snap(150, 5, tol_m=20)
    G2 = apply_road_cuts_to_graph(G, nl, tn, [{"edge_from": s["edge_from"], "edge_to": s["edge_to"],
                                              "x": s["x"], "y": s["y"]}], Cfg())
    assert not G2.has_edge((100.0, 0.0), (200.0, 0.0))
    assert G2.has_edge((0.0, 0.0), (100.0, 0.0)) and G2.has_edge((100.0, 0.0), (100.0, 100.0))   # simpang tetap
    assert G.has_edge((100.0, 0.0), (200.0, 0.0))                                                 # graf asli utuh

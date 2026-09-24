"""Diagnostik dan perapian topologi jaringan (analisis sensitivitas)."""
import geopandas as gpd
import networkx as nx
import numpy as np
from shapely.geometry import LineString

from scripts import topologi as TP


def _roads(lines, bridge=None):
    n = len(lines)
    return gpd.GeoDataFrame({"bridge": bridge or ["F"] * n, "tunnel": ["F"] * n, "layer": [0] * n},
                            geometry=[LineString(c) for c in lines], crs="EPSG:32749")


def test_graf_sama_dengan_engine():
    from backend.engine import Cfg, build_road_graph
    r = _roads([[(0, 0), (10, 0)], [(10, 0), (20, 0)], [(10, 0), (10, 10)]])
    r["banjir"] = 0
    G1, _, _ = build_road_graph(r, "banjir", 0.0, Cfg())
    G2, _, _ = TP.graph_from_edges(TP.edges_from_roads(r))
    assert set(map(frozenset, G1.edges())) == set(map(frozenset, G2.edges()))


def test_perpotongan_dan_noding():
    # dua jalan bersilangan tanpa simpul bersama; satu jembatan melintas
    r = _roads([[(0, 0), (20, 0)], [(10, -10), (10, 10)], [(5, -10), (5, 10)]], bridge=["F", "F", "T"])
    e = TP.edges_from_roads(r)
    cr = TP.crossings(e)
    assert len(cr) == 2 and cr["khusus"].sum() == 1
    G0, _, _ = TP.graph_from_edges(e)
    assert nx.number_connected_components(G0) == 3
    c = TP.cleaned_edges(e, cr, TP.near_misses(e, G0), tol=1.0)
    G1, _, _ = TP.graph_from_edges(c)
    assert G1.has_node((10.0, 0.0)) and G1.degree((10.0, 0.0)) == 4       # perpotongan biasa disambung
    assert not G1.has_node((5.0, 0.0))                                   # jembatan tidak disambung
    assert nx.number_connected_components(G1) == 2


def test_near_miss_dan_sambungan():
    # jalan B berakhir 0,8 m dari jalan A (tidak tersambung); jalan C 3 m
    r = _roads([[(0, 0), (40, 0)], [(20, 0.8), (20, 30)], [(35, 3.0), (35, 30)]])
    e = TP.edges_from_roads(r)
    G, _, _ = TP.graph_from_edges(e)
    nm = TP.near_misses(e, G, tol_max=5)
    d = sorted(nm["dist"].round(2).tolist())
    assert d == [0.8, 3.0]
    c1 = TP.cleaned_edges(e, TP.crossings(e), nm, tol=1.0)
    G1, _, _ = TP.graph_from_edges(c1)
    assert nx.number_connected_components(G1) == 2                       # hanya B tersambung (0,8 ≤ 1 m)
    assert nx.has_path(G1, (0.0, 0.0), (20.0, 30.0))
    c2 = TP.cleaned_edges(e, TP.crossings(e), nm, tol=5.0)
    assert nx.number_connected_components(TP.graph_from_edges(c2)[0]) == 1


def test_near_miss_mengecualikan_tetangga_jaringan():
    # ujung buntu yang dekat dengan sisi di jalan yang sama (terjangkau ≤ 20 m) bukan near-miss
    r = _roads([[(0, 0), (5, 0)], [(5, 0), (5, 3)], [(5, 3), (0.5, 0.5)]])
    e = TP.edges_from_roads(r)
    G, _, _ = TP.graph_from_edges(e)
    assert len(TP.near_misses(e, G, tol_max=5)) == 0


def test_sisi_level_menghapus_sambungan_ruas_ditutup():
    r = _roads([[(0, 0), (40, 0)], [(20, 0.8), (20, 30)]])
    e = TP.edges_from_roads(r)
    G, _, _ = TP.graph_from_edges(e)
    c = TP.cleaned_edges(e, TP.crossings(e), TP.near_misses(e, G), tol=1.0)
    lv = TP.edges_for_level(c, np.array([False, True]))
    assert (lv.src != 1).all() and (lv.src2 != 1).all()


def test_titik_pecah_miring_menjadi_simpul_yang_sama():
    # sisi miring: titik proyeksi tidak bulat; sambungan harus mendarat di simpul pecahan yang sama
    r = _roads([[(0.003, 0.007), (37.119, 23.451)], [(15.5, 10.3), (15.5, 40.0)]])
    e = TP.edges_from_roads(r)
    G, _, _ = TP.graph_from_edges(e)
    nm = TP.near_misses(e, G, tol_max=5)
    assert len(nm) == 1 and nm["dist"].iloc[0] < 1.0
    c = TP.cleaned_edges(e, TP.crossings(e), nm, tol=1.0)
    G1, _, _ = TP.graph_from_edges(c)
    assert nx.number_connected_components(G1) == 1
    # perpotongan miring: kedua sisi dipecah pada simpul yang sama
    r2 = _roads([[(0.0, 0.0), (10.013, 7.771)], [(0.0, 7.0), (10.0, 0.337)]])
    e2 = TP.edges_from_roads(r2)
    c2 = TP.cleaned_edges(e2, TP.crossings(e2), TP.near_misses(e2, TP.graph_from_edges(e2)[0]), tol=1.0)
    assert nx.number_connected_components(TP.graph_from_edges(c2)[0]) == 1

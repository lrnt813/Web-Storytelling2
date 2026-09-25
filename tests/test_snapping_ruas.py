"""Putaran 6: snapping ke RUAS terdekat (proyeksi tegak lurus + simpul virtual)."""
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pytest
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import Point

from backend.engine import (Cfg, SNAP_MAX_M, compute_distances, graph_edge_arrays, snap_points,
                            snap_to_segments, snapped_network)
from backend.thesis import detect_tas_detour

DATA = Path(__file__).resolve().parents[1] / "data"


def _pack(edges):
    G = nx.Graph()
    for a, b in edges:
        G.add_edge(a, b, weight=float(np.hypot(b[0] - a[0], b[1] - a[1])))
    nl = np.array(list(G.nodes()))
    return G, nl, cKDTree(nl)


def _jalan_panjang():
    # jalan A: satu ruas panjang (0,0)–(1000,0) tanpa verteks tengah;
    # jalan B: cabang yang verteksnya (500,60) dekat titik uji, terhubung ke A hanya lewat ujung x = 1000
    return _pack([((0.0, 0.0), (1000.0, 0.0)),
                  ((500.0, 60.0), (500.0, 500.0)), ((500.0, 500.0), (1000.0, 500.0)),
                  ((1000.0, 500.0), (1000.0, 0.0))])


def test_a_jarak_snapping_ruas_tidak_lebih_besar_dari_verteks():
    G, nl, tn = _jalan_panjang()
    rng = np.random.RandomState(0)
    xy = rng.uniform(-200, 1200, size=(500, 2))
    ea, eb, _ = graph_edge_arrays(G, nl)
    d_ruas, _, _, ok_r = snap_to_segments(xy, nl, ea, eb)
    d_vert, _, ok_v = snap_points(xy, tn)
    assert np.all(ok_r | ~ok_v)                          # yang ter-snap ke verteks pasti ter-snap ke ruas
    assert np.all(d_ruas[ok_r] <= d_vert[ok_r] + 1e-9)


@pytest.mark.skipif(not (DATA / "Kulonprogo_Ready4.gpkg").exists(), reason="data tidak tersedia")
def test_a_data_asli_jarak_snapping_ruas_tidak_lebih_besar_dari_verteks():
    from backend import thesis as T
    from backend.engine import build_road_graph, load_data, load_road_network
    cfg = Cfg(base_dir=str(DATA))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    G, nl, tn = build_road_graph(roads, T.SKENARIO, 0.0, cfg)
    xy = np.column_stack([gdf["cx"].values, gdf["cy"].values])
    txy = np.concatenate([np.column_stack([t.geometry.x.values, t.geometry.y.values]) for t in tes.values()])
    ea, eb, _ = graph_edge_arrays(G, nl)
    for pts in (xy, txy):
        d_ruas, _, _, ok_r = snap_to_segments(pts, nl, ea, eb)
        d_vert, _, ok_v = snap_points(pts, tn)
        assert np.all(ok_r | ~ok_v)
        assert np.all(d_ruas[ok_r] <= d_vert[ok_r] + 1e-6)


def test_b_titik_tersambung_ke_ruas_panjang_bukan_verteks_jalan_lain():
    G, nl, tn = _jalan_panjang()
    cfg = Cfg()
    grid = pd.DataFrame({"cx": [500.0], "cy": [20.0]})     # 20 m dari ruas A, 40 m dari verteks (500, 60)
    tes = gpd.GeoDataFrame({"kategori": ["ibadah"]}, geometry=[Point(520.0, -10.0)], crs=cfg.target_crs)
    d_vert, i_vert, _ = snap_points(np.array([[500.0, 20.0]]), tn)
    assert tuple(nl[i_vert[0]]) == (500.0, 60.0)            # snapping verteks memilih jalan B
    tpk, _, _, _, _ = compute_distances(grid, "banjir", tes, cfg, 0.0, 400.0, None, None, G, nl, tn)
    v = cfg.walking_speed_m_per_min
    assert np.isclose(tpk["ibadah"][0], (20 + 20 + 10) / v)  # ruas snapping 20 m + 20 m sepanjang A + 10 m
    res = detect_tas_detour(pd.DataFrame(index=[0]), np.array([[500.0, 20.0]]), tes, (G, nl, tn), 400.0, cfg)
    assert np.isclose(res["t_aktual"][0], 50.0 / v)          # batas minimum 50 m


def test_c_total_panjang_ruas_dipecah_sama_dengan_panjang_asli():
    G, nl, _ = _jalan_panjang()
    pts = np.array([[100.0, 5.0], [700.0, -3.0], [250.0, 1.0], [700.0, 8.0], [1000.0, 250.0]])
    sn = snapped_network(G, nl, [pts])
    csr = sn["csr"]
    assert np.isclose(csr.sum() / 2, sum(w for _, _, w in G.edges(data="weight")))
    # ruas A (0,0)–(1000,0) dipecah pada x = 100, 250, 700 (dua titik berbagi posisi 700)
    d, node, ok = sn["sets"][0][:3]
    assert ok.all() and node[1] == node[3]
    assert csr.shape[0] == len(nl) + 4                       # 3 simpul virtual di A + 1 di sisi x = 1000
    ia = {tuple(p): i for i, p in enumerate(map(tuple, nl))}
    D = dijkstra(csr, directed=False, indices=ia[(0.0, 0.0)])
    assert np.isclose(D[ia[(1000.0, 0.0)]], 1000.0)
    assert np.allclose(D[node[[0, 2, 1]]], [100.0, 250.0, 700.0])


def test_d_jarak_jaringan_dua_titik_pada_segmen_sama_sama_dengan_jarak_sepanjang_segmen():
    G, nl, tn = _pack([((0.0, 0.0), (300.0, 400.0))])        # ruas miring 500 m
    cfg = Cfg()
    a, b = np.array([60.0, 80.0]), np.array([240.0, 320.0])  # posisi 100 m dan 400 m sepanjang ruas
    nrm = np.array([-0.8, 0.6])
    ga, tb = a + 7 * nrm, b - 4 * nrm
    sn = snapped_network(G, nl, [ga[None], tb[None]])
    (dg, ng, _), (dt, nt, _) = sn["sets"][0][:3], sn["sets"][1][:3]
    assert np.isclose(dg[0], 7) and np.isclose(dt[0], 4)
    D = dijkstra(sn["csr"], directed=False, indices=int(ng[0]))
    assert np.isclose(D[nt[0]], 300.0)
    grid = pd.DataFrame({"cx": [ga[0]], "cy": [ga[1]]})
    tes = gpd.GeoDataFrame({"kategori": ["gor"]}, geometry=[Point(*tb)], crs=cfg.target_crs)
    tpk, _, _, _, _ = compute_distances(grid, "banjir", tes, cfg, 0.0, 400.0, None, None, G, nl, tn)
    assert np.isclose(tpk["gor"][0], (7 + 300 + 4) / cfg.walking_speed_m_per_min)


def test_batas_snapping_300_m_tetap_berlaku():
    G, nl, tn = _jalan_panjang()
    ea, eb, _ = graph_edge_arrays(G, nl)
    d, e, _, ok = snap_to_segments(np.array([[500.0, -SNAP_MAX_M - 1], [500.0, -SNAP_MAX_M + 1]]), nl, ea, eb)
    assert list(ok) == [False, True] and e[0] == -1

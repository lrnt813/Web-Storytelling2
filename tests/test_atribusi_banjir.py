"""Putaran 6: atribusi pengaruh banjir pada TAS dan rute jaringan TAS."""
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import LineString

from backend import thesis as T


def _tas(status, t_akt, ids):
    return {"status": np.array(status), "t_aktual": np.array(t_akt, float), "id_tes_terdekat": np.array(ids, object)}


def _jalan():
    # jalan lurus x = 0..1000 (4 segmen 250 m) di y = 0
    xs = [0.0, 250.0, 500.0, 750.0, 1000.0]
    roads = gpd.GeoDataFrame({"banjir": [0, 0, 3, 0]},
                             geometry=[LineString([(a, 0.0), (b, 0.0)]) for a, b in zip(xs[:-1], xs[1:])],
                             crs="EPSG:32749")
    G = nx.Graph()
    for a, b in zip(xs[:-1], xs[1:]):
        G.add_edge((a, 0.0), (b, 0.0), weight=b - a)
    nl = np.array(list(G.nodes()))
    return roads, (G, nl, cKDTree(nl))


def test_aturan_atribusi():
    roads, pack = _jalan()
    # grid: 0 dipicu, 1 diperparah, 2 tidak berubah, 3 TES berubah, 4 T_aktual turun, 5 waktu Baseline ≥ 30,
    #       6 TES tidak terjangkau di Baseline, 7 bukan TAS di level ini
    base = _tas([0, 1, 1, 1, 1, 0, 2, 0], [10, 35, 40, 40, 50, 31, 403, 5], ["a", "a", "a", "a", "a", "a", "a", "a"])
    lev = _tas([1, 1, 1, 1, 1, 1, 1, 0], [45, 60, 40.8, 41, 45, 35, 60, 5], ["a", "a", "a", "b", "a", "a", "a", "a"])
    gxy = np.array([[100.0, 20.0]] * 8)
    closed = np.array([False, False, True, False])
    df = T.flood_attribution(gxy, base, lev, {"a": (900.0, -10.0)}, closed, pack, T.segment_lookup(roads))
    got = dict(zip(df["id_grid"], df["atribusi"]))
    assert got == {0: "dipicu banjir", 1: "diperparah banjir", 2: "tidak berubah", 3: "lainnya", 4: "lainnya",
                   5: "lainnya", 6: "lainnya"}
    kat = dict(zip(df["id_grid"], df["alasan_kategori"]))
    assert kat[3] == "TES terdekat berubah" and kat[4] == "T_aktual turun"
    assert kat[5] == "waktu Baseline ≥ batas" and kat[6] == "TES tidak terjangkau di Baseline"
    r0 = df.set_index("id_grid").loc[0]
    assert np.isclose(r0["waktu_baseline_tes_sama"], 10) and np.isclose(r0["tambahan_waktu"], 35)
    # rute Baseline (100,20) → (900,-10) melewati segmen 0..3; hanya segmen 2 (500–750, 250 m) ditutup
    assert r0["ruas_tertutup_n"] == 1 and np.isclose(r0["ruas_tertutup_m"], 250.0)
    assert np.isnan(df.set_index("id_grid").loc[2, "ruas_tertutup_n"])       # tidak berubah: tidak dihitung
    s = T.attribution_summary(df)
    assert s["jumlah_tas"] == 7 and s["kelompok"]["lainnya"]["jumlah"] == 4
    assert np.isclose(s["kelompok"]["dipicu banjir"]["persen"], 100 / 7)
    assert s["median_waktu_baseline_dipicu"] == 10 and s["median_tambahan_waktu_diperparah"] == 25


def test_ambang_satu_menit_inklusif():
    roads, pack = _jalan()
    base = _tas([1, 1], [40, 40], ["a", "a"])
    lev = _tas([1, 1], [41.0, 41.01], ["a", "a"])
    df = T.flood_attribution(np.array([[100.0, 20.0]] * 2), base, lev, {"a": (900.0, -10.0)},
                             np.zeros(4, bool), pack, T.segment_lookup(roads))
    assert list(df["atribusi"]) == ["tidak berubah", "diperparah banjir"]


def test_rute_tas_sama_dengan_jarak_ruas_snapping():
    _, pack = _jalan()
    r = T.tas_routes(pack, np.array([[100.0, 20.0], [100.0, 900.0]]), np.array([[900.0, -10.0], [900.0, -10.0]]))
    assert r[1] is None                                                  # gagal snapping (> 300 m)
    assert np.isclose(r[0]["jarak_m"], 20 + 800 + 10)
    assert r[0]["xy"][0] == (100.0, 20.0) and r[0]["xy"][-1] == (900.0, -10.0)
    assert np.allclose(r[0]["xy"][1], (100.0, 0.0)) and np.allclose(r[0]["xy"][-2], (900.0, 0.0))
    assert len(r[0]["sisi"]) == 4                                        # sisi pecahan dipetakan ke induknya


def test_kolom_grid_atribusi():
    roads, pack = _jalan()
    base = _tas([0, 1, 0], [10, 35, 5], ["a", "a", "a"])
    lev = _tas([1, 1, 0], [45, 60, 5], ["a", "a", "a"])
    df = T.flood_attribution(np.array([[100.0, 20.0]] * 3), base, lev, {"a": (900.0, -10.0)},
                             np.zeros(4, bool), pack, T.segment_lookup(roads))
    fr = T.attribution_grid_frame("sedang", df, 3)
    a = fr["atribusi_banjir_sedang"]
    assert list(a[:2]) == ["dipicu banjir", "diperparah banjir"] and pd.isna(a[2])
    assert np.isclose(fr["tambahan_waktu_sedang"][1], 25) and np.isnan(fr["tambahan_waktu_sedang"][2])
    assert fr["ruas_tertutup_rute_baseline_n_sedang"][0] == 0


def test_records_dashboard_memuat_atribusi_bila_ada():
    from backend.engine import Cfg
    cfg = Cfg()
    base = {"id_grid": [0, 1], "id_grid_asli": ["a", "b"], T.SKENARIO: [0, 1], "Road_Density_mean": [1.0, 2.0]}
    for key in ("baseline", "sedang"):
        base.update({f"cl_{key}_k4": [0, 1], f"mem_{key}_k4": [0.9, 0.8], f"tergenang_{key}": [0, 0],
                     f"waktu_min_{key}": [5.0, 40.0], f"opsi_{key}": [5, 5], f"t_ideal_{key}": [1.0, 2.0],
                     f"t_aktual_{key}": [5.0, 40.0], f"di_{key}": [5.0, 20.0], f"tas_{key}": [0, 1],
                     f"tas_status_{key}": [0, 1], f"tas_status_persentil_{key}": [0, 1],
                     f"tes_terdekat_{key}": ["gor", "gor"], f"akses_{key}": [0, 1],
                     **{f"waktu_{k}_{key}": [5.0, 40.0] for k in cfg.kategori_fac}})
    grid = pd.DataFrame(base)
    grid["atribusi_banjir_sedang"] = [None, "dipicu banjir"]
    grid["tambahan_waktu_sedang"] = [np.nan, 12.5]
    rs = T.records_from_grid(grid, "sedang", cfg, 4)
    assert rs[1]["atribusi_banjir"] == "dipicu banjir" and rs[1]["tambahan_waktu_tas"] == 12.5
    assert rs[0]["atribusi_banjir"] is None
    rb = T.records_from_grid(grid, "baseline", cfg, 4)
    assert rb[1]["atribusi_banjir"] is None and rb[1]["tambahan_waktu_tas"] is None

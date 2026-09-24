"""Putaran 4: satu konstanta batas waktu evakuasi, aturan TAS dengan syarat T_aktual,
kategori akses (Li dkk. 2026), dan perubahan TAS terhadap Baseline."""
import io
import tokenize
from pathlib import Path

import numpy as np
import pandas as pd

from backend import engine as E
from backend import thesis as T

ROOT = Path(__file__).resolve().parents[1]


def test_konstanta_tunggal_batas_waktu():
    assert E.EVAC_TIME_MIN == 30.0 and tuple(E.EVAC_TIME_SENS) == (20.0, 40.0)
    assert T.TAS_T_AKTUAL_MIN == E.EVAC_TIME_MIN == E.Cfg().isolation_time_threshold
    assert E.REDCAPManual.__init__.__defaults__[-1] == E.EVAC_TIME_MIN


def test_tidak_ada_angka_30_tertanam():
    """Literal numerik 30 / 30.0 hanya boleh muncul di definisi EVAC_TIME_MIN (engine.py)."""
    found = []
    for f in list((ROOT / "backend").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.NUMBER and float(tok.string) == 30.0:
                line = tok.line.strip()
                if not (f.name == "engine.py" and line.startswith("EVAC_TIME_MIN")):
                    found.append(f"{f.name}:{tok.start[0]}: {line}")
    assert not found, "angka 30 tertanam:\n" + "\n".join(found)


def test_kategori_akses():
    w = np.array([5.0, 30.0, 30.5, 400.0, 3.0])
    wet = np.array([0, 0, 0, 0, 1])
    cat = T.access_category(w, wet, t_pen=400.0)
    assert cat.tolist() == [0, 0, 1, 2, 3]
    assert T.access_category(w, wet, 400.0, threshold=20.0).tolist() == [0, 1, 1, 2, 3]
    s = T.access_summary(cat)
    assert s["Jauh"]["jumlah_grid"] == 1 and np.isclose(s["Terjangkau"]["persen"], 40.0)
    tr = T.access_transition(cat, np.array([0, 1, 1, 3, 3]))
    assert tr["matrix"][0][1] == 1 and tr["tetap"] == 3


def test_perubahan_tas():
    base = np.array([1, 1, 1, 1, 0, 2, 0])
    lvl = np.array([1, 3, 2, 0, 1, 1, 0])
    ch = T.tas_change(base, lvl)
    assert ch["tas_tetap"] == 1 and ch["tas_hilang"] == 3
    assert (ch["tas_hilang_jadi_tergenang"], ch["tas_hilang_jadi_terputus"], ch["tas_hilang_lainnya"]) == (1, 1, 1)
    assert ch["tas_baru"] == 2 and ch["tas_baru_dari_status_baseline"] == {"Non-TAS": 1, "Terputus": 1}


def test_aturan_tas_syarat_t_aktual():
    """Grid dekat (T_ideal ≤ 5) dengan DI ≥ 2: TAS hanya bila T_aktual ≥ 30 menit."""
    import geopandas as gpd
    import networkx as nx
    from scipy.spatial import cKDTree
    from shapely.geometry import Point
    G = nx.Graph()
    # jalan lurus 0..3000 m di y = 0; TES di (0, 0); grid di y = 150 dekat TES tetapi hanya
    # terhubung lewat cabang panjang dari x = 3000
    xs = np.arange(0, 3001, 100.0)
    for a, b in zip(xs[:-1], xs[1:]):
        G.add_edge((a, 0.0), (b, 0.0), weight=100.0)
    G.add_edge((3000.0, 0.0), (3000.0, 150.0), weight=150.0)
    G.add_edge((3000.0, 150.0), (60.0, 150.0), weight=2940.0)
    nl = np.array(list(G.nodes()))
    grid_xy = np.array([[60.0, 160.0], [60.0, 10.0]])
    tes = gpd.GeoDataFrame({"kategori": ["ibadah"]}, geometry=[Point(0.0, 0.0)], crs="EPSG:32749")
    res = T.detect_tas_detour(pd.DataFrame(index=range(2)), grid_xy, tes, (G, nl, cKDTree(nl)), 400.0, E.Cfg())
    t_akt, di, ti = res["t_aktual"], res["detour_index"], res["t_ideal"]
    assert t_akt[0] >= 30 and di[0] >= 2 and ti[0] <= 5 and res["status"][0] == 1
    assert res["status"][1] == 0
    s = res["summary"]
    assert s["sensitivitas_ambang_waktu"]["40"]["jumlah_tas"] == int(t_akt[0] >= 40)
    assert s["sensitivitas_absolut_v3"]["jumlah_tas"] >= s["jumlah_tas"]

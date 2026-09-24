"""Uji deteksi Titik Aman Semu (Langkah 6) pada graf jalan sintetis."""
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point

from backend.engine import Cfg
from backend.thesis import TAS_DI_ABSOLUTE, TAS_MIN_EUCLID_M, detect_tas_detour


def _setup():
    """Jalan lurus sepanjang y = 0 (x = 0..2000 m, simpul tiap 100 m) + satu TES di (1000, 0).
    Grid di atas jalan (dekat, lurus), grid di seberang sungai yang harus memutar,
    dan satu grid yang tidak bisa di-snap (terputus)."""
    G = nx.Graph()
    xs = np.arange(0, 2001, 100.0)
    for a, b in zip(xs[:-1], xs[1:]):
        G.add_edge((a, 0.0), (b, 0.0), weight=100.0)
    # cabang memutar: dari ujung (2000,0) naik ke (2000,150) lalu kembali ke (1050,150)
    G.add_edge((2000.0, 0.0), (2000.0, 150.0), weight=150.0)
    G.add_edge((2000.0, 150.0), (1050.0, 150.0), weight=950.0)
    nl = np.array(list(G.nodes()))
    grid_xy = np.array([[x, 20.0] for x in range(0, 2001, 100)]            # di sisi jalan
                       + [[1050.0, 170.0], [1060.0, 165.0]]                 # dekat TES (~177 m), jalur memutar ~2,1 km
                       + [[5000.0, 5000.0]], float)                         # di luar jangkauan snapping
    tes = gpd.GeoDataFrame({"kategori": ["ibadah"]}, geometry=[Point(1000.0, 0.0)], crs="EPSG:32749")
    return grid_xy, tes, (G, nl, cKDTree(nl))


def test_terputus_dikeluarkan_dan_jarak_minimum():
    grid_xy, tes, pack = _setup()
    cfg = Cfg()
    t_pen = 400.0
    res = detect_tas_detour(pd.DataFrame(index=range(len(grid_xy))), grid_xy, tes, pack, t_pen, cfg)
    st, s = res["status"], res["summary"]
    assert st[-1] == 2 and np.isnan(res["detour_index"][-1])          # terputus
    assert s["jumlah_terputus"] == 1
    assert s["jumlah_tas"] + s["jumlah_non_tas"] + s["jumlah_terputus"] == len(grid_xy)
    # jarak Euclidean minimum 50 m
    assert res["t_ideal"].min() >= TAS_MIN_EUCLID_M / cfg.walking_speed_m_per_min - 1e-12
    # grid di seberang (dekat secara Euclidean, jalur memutar jauh) terdeteksi TAS
    assert st[len(grid_xy) - 3] == 1
    # persentil dihitung hanya dari grid terjangkau
    reach = st != 2
    assert np.isclose(s["p25_t_ideal"], np.percentile(res["t_ideal"][reach], 25))
    assert s["sensitivitas_di_absolut"]["ambang_di"] == TAS_DI_ABSOLUTE

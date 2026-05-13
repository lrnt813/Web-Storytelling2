# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  engine.py — Computation Engine                                              ║
# ║  Tipologi Kerawanan Evakuasi & Deteksi Titik Aman Semu                       ║
# ║  Kabupaten Kulon Progo                                                       ║
# ║                                                                              ║
# ║  STRICT RULES APPLIED:                                                       ║
# ║  ✔  Logika inti algoritma TIDAK DIUBAH (SDWFCM, SFCM, REDCAP, SKATER)       ║
# ║  ✔  Semua visualisasi Matplotlib/Folium DIHAPUS                              ║
# ║  ✔  Semua disk I/O (.to_file, .to_csv, ZIP) DIHAPUS                         ║
# ║  ✔  log()/section()/kv()/tbl() terminal diganti Python logging              ║
# ║  ✔  File ini TIDAK bergantung pada FastAPI — murni komputasi                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import logging
import math
import time
import heapq
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import scipy.sparse as sp
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from scipy.sparse import csr_matrix
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PowerTransformer, RobustScaler

from libpysal.weights import KNN, Queen, Rook
from esda.moran import Moran

warnings.filterwarnings("ignore")
_SDWFCM_W_CACHE: Dict[tuple, csr_matrix] = {}
_SDWFCM_SIGMA_CACHE: Dict[tuple, float] = {}

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    from numba import jit
    NUMBA_OK = True
except ImportError:
    NUMBA_OK = False
    def jit(*a, **k):
        def d(fn): return fn
        return d

try:
    from kneed import KneeLocator
    KNEED_OK = True
except ImportError:
    KNEED_OK = False

PANDANA_OK = False

try:
    from spopt.region import Skater
    SKATER_OK = True
except ImportError:
    SKATER_OK = False

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *a, **k): return iterable  # silent fallback

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 2. KONFIGURASI (Cfg)
#    Semua path file dan hyperparameter algoritma ada di sini.
#    Sesuaikan DATA_DIR di main.py saat startup.
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Cfg:
    """Konfigurasi terpusat untuk seluruh pipeline.
    Catatan: bab_subdirs dan output_dir DIHAPUS — tidak relevan untuk API.
    """
    # ── Path data (di-override dari main.py via environment / argumen) ────────
    base_dir: str = "./data"
    target_crs: str = "EPSG:32749"

    # ── Kolom hazard ──────────────────────────────────────────────────────────
    hazard_col_map: Dict[str, str] = field(default_factory=lambda: {
        "banjir":          "banjir",
        "banjir_bandang":  "banjir_bandang",
        "tanah_longsor":   "tanah_longsor",
    })
    skenario_list: List[str] = field(default_factory=lambda: [
        "banjir", "banjir_bandang", "tanah_longsor",
    ])
    intensity_levels: List[float] = field(default_factory=lambda: [
        0.0, 0.25, 0.50, 0.75, 1.00,
    ])
    indeks_bahaya: Dict[str, str] = field(default_factory=lambda: {
        "banjir":         "banjir",
        "banjir_bandang": "banjir_bandang",
        "tanah_longsor":  "tanah_longsor",
    })
    kategori_fac: List[str] = field(default_factory=lambda: [
        "pendidikan", "kesehatan", "pemerintahan", "ibadah", "gor",
    ])
    variabel_dasar: List[str] = field(default_factory=lambda: [
        "Road_Density_mean",
    ])
    hazard_normalize_map: Dict[int, float] = field(default_factory=lambda: {
        0: 0.00, 1: 0.33, 2: 0.67, 3: 1.00,
    })

    # ── Threshold & bobot aksesibilitas ──────────────────────────────────────
    impact_closure_threshold: float = 0.20
    tes_hazard_threshold: int = 2
    road_break_threshold: int = 3
    road_damaged_weight_multiplier: float = 3.0
    walking_speed_m_per_min: float = 80.0
    golden_time_min: float = 15.0
    isolation_time_threshold: float = 30.0
    isolation_penalty_weight: float = 10.0
    unreachable_time: float = 9999.0

    # ── SDWFCM — Algoritma Utama ──────────────────────────────────────────────
    sdwfcm_m: float = 1.7
    sdwfcm_alpha: float = 0.5
    sdwfcm_sigma: Optional[float] = None
    sdwfcm_knn: int = 8
    sdwfcm_max_iter: int = 150
    sdwfcm_tol: float = 1e-4

    # ── SFCM — Pembanding 1 ───────────────────────────────────────────────────
    sfcm_m: float = 2.0
    sfcm_alpha: float = 0.5
    sfcm_max_iter: int = 150
    sfcm_tol: float = 1e-4

    # ── REDCAP — Pembanding 2 ─────────────────────────────────────────────────
    redcap_linkage: str = "ward"
    size_alpha: float = 1.0

    # ── SKATER — Pembanding 3 ─────────────────────────────────────────────────
    skater_min_region: int = 10

    # ── K-Optimal ────────────────────────────────────────────────────────────
    k_range: range = field(default_factory=lambda: range(2, 11))
    k_min_parsimony: int = 2
    elbow_n_init: int = 5
    elbow_max_iter: int = 100

    # ── Titik Aman Semu (Academic Version) ───────────────────────────────────
    psi_threshold_fragile: float = 0.25
    psi_threshold_robust: float = 0.1
    alr_threshold_severe: float = 0.75
    alr_threshold_minor: float = 0.25

    def __post_init__(self):
        b = self.base_dir
        self.input_file  = f"{b}/Kulonprogo_Ready4.gpkg"
        self.roads_file  = f"{b}/Kulonprogo_Jalan.gpkg"
        self.tes_files   = {
            "pendidikan":   f"{b}/Kulonprogo_Pendidikan.gpkg",
            "kesehatan":    f"{b}/Kulonprogo_Faskes.gpkg",
            "pemerintahan": f"{b}/Kulonprogo_Kantor.gpkg",
            "ibadah":       f"{b}/Kulonprogo_Ibadah.gpkg",
            "gor":          f"{b}/Kulonprogo_GOR.gpkg",
        }

    def sk_key(self, s: str, i: float) -> str:
        return f"{s}_{int(i * 100)}pct"

    def int_label(self, i: float) -> str:
        return "Baseline (0%)" if i == 0.0 else f"Intensitas {int(i * 100)}%"

    def norm_haz(self, v: int) -> float:
        return self.hazard_normalize_map.get(int(v), 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# 3. DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
def _read_gpkg(path: str, crs_target: str, geom_types=None) -> gpd.GeoDataFrame:
    """Baca GeoPackage, reproject ke CRS target, dan filter tipe geometri."""
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    if gdf.crs.to_epsg() != int(crs_target.split(":")[1]):
        gdf = gdf.to_crs(crs_target)
    if geom_types:
        gdf = gdf[gdf.geometry.geom_type.isin(geom_types)]
    return gdf.reset_index(drop=True)


def load_data(cfg: Cfg) -> gpd.GeoDataFrame:
    """
    Baca GeoPackage grid utama Kulon Progo.

    PERUBAHAN v2: Tambah kolom `id_grid` sebagai primary key integer urut 0..N-1.
    Urutan operasi IDENTIK dengan export_geometry.py untuk menjamin sinkronisasi:
      1. _read_gpkg  (baca + reproject ke ENGINE_CRS=EPSG:32749)
      2. filter: notna() & ~is_empty()
      3. reset_index(drop=True)
      4. id_grid = range(N)   <-- BARU
    """
    gdf = _read_gpkg(cfg.input_file, cfg.target_crs)

    # Filter geometri null/empty — IDENTIK dengan export_geometry.py
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)

    # ── BARU: id_grid sebagai primary key JOIN antara API dan geometri statis ──
    # PERINGATAN: Jangan ubah urutan operasi di atas baris ini.
    # Perubahan urutan = id_grid tidak sinkron dengan static_grid_kulonprogo.geojson.
    if "id_grid" in gdf.columns:
        logger.warning(
            "[load_data] Kolom 'id_grid' sudah ada di GPKG -> ditimpa ulang "
            "dengan integer urut 0..N-1 (menjamin sinkronisasi dengan geometri statis)."
        )
    gdf["id_grid"] = range(len(gdf))
    gdf["id_grid"] = gdf["id_grid"].astype("int32")

    # ── BARU: Precompute centroid untuk mempercepat routing ──
    logger.info("[load_data] Precomputing centroids...")
    centroids = gdf.geometry.centroid
    gdf["cx"] = centroids.x
    gdf["cy"] = centroids.y

    logger.info(
        f"[load_data] {len(gdf)} grid dimuat | "
        f"CRS={gdf.crs.to_epsg()} | "
        f"id_grid: 0..{len(gdf) - 1}"
    )
    return gdf


def load_road_network(cfg: Cfg) -> Tuple[Optional[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]:
    """Baca GeoPackage jalan dan semua layer TES."""
    import os
    roads = None
    if os.path.exists(cfg.roads_file):
        roads = _read_gpkg(cfg.roads_file, cfg.target_crs, ["LineString", "MultiLineString"])
        for c in cfg.hazard_col_map.values():
            if c not in roads.columns:
                roads[c] = 0
        logger.info(f"[load_road_network] Jalan: {len(roads)} segmen")
    else:
        logger.warning(f"[load_road_network] File jalan tidak ada: {cfg.roads_file}")

    tes: Dict[str, gpd.GeoDataFrame] = {}
    for kat, fp in cfg.tes_files.items():
        if os.path.exists(fp):
            t = _read_gpkg(fp, cfg.target_crs, ["Point"])
            for c in cfg.hazard_col_map.values():
                if c not in t.columns:
                    t[c] = 0
            tes[kat] = t
            logger.info(f"[load_road_network] TES {kat}: {len(t)} titik")
        else:
            logger.warning(f"[load_road_network] TES tidak ada: {fp}")
    return roads, tes


# ══════════════════════════════════════════════════════════════════════════════
# 4. SPATIAL WEIGHT MATRIX
#    ⚠ LOGIKA INTI — JANGAN UBAH
# ══════════════════════════════════════════════════════════════════════════════
def build_weights(gdf: gpd.GeoDataFrame):
    """Bangun matriks bobot spasial Rook (fallback Queen).
    Pulau (island) ditangani dengan KNN fallback.
    Komponen tidak terhubung disambungkan via edge MST terdekat.
    """
    n = len(gdf)
    try:
        w = Rook.from_dataframe(gdf, ids=None, silence_warnings=True)
    except Exception:
        w = Queen.from_dataframe(gdf, silence_warnings=True)

    # ── KNN fallback untuk island ─────────────────────────────────────────────
    islands = [i for i, nb in w.neighbors.items() if len(nb) == 0]
    if islands:
        try:
            wk = KNN.from_dataframe(gdf, k=2, silence_warnings=True)
            for i in islands:
                w.neighbors[i] = list(wk.neighbors[i])
                w.weights[i]   = [1.0] * len(wk.neighbors[i])
        except Exception as e:
            logger.warning(f"[build_weights] KNN fallback gagal: {e}")

    # ── Sambungkan komponen terputus ──────────────────────────────────────────
    def _add(u, v):
        for a, b in [(u, v), (v, u)]:
            if b not in w.neighbors.get(a, []):
                w.neighbors[a] = list(w.neighbors.get(a, [])) + [b]
                w.weights[a]   = list(w.weights.get(a, []))   + [1.0]

    Gx = nx.Graph()
    Gx.add_nodes_from(range(n))
    for i, nbs in w.neighbors.items():
        for j in nbs:
            Gx.add_edge(i, j)
    comps = list(nx.connected_components(Gx))
    if len(comps) > 1:
        cents = np.array([[g.centroid.x, g.centroid.y] for g in gdf.geometry])
        cl    = [sorted(c) for c in comps]
        tu    = cKDTree(cents)
        u2c   = np.zeros(n, int)
        for ci, cu in enumerate(cl):
            for u in cu:
                u2c[u] = ci
        parent = list(range(len(comps)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
                return True
            return False

        for ci in sorted(range(len(comps)), key=lambda i: len(cl[i])):
            if find(ci) == find(0) and ci != 0:
                continue
            cc = cents[cl[ci]].mean(0)
            _, idxs = tu.query(cc, k=min(200, n))
            for idx in idxs:
                cj = int(u2c[int(idx)])
                if find(cj) != find(ci):
                    diffs   = cents[cl[ci]] - cents[int(idx)]
                    nearest = cl[ci][int(np.argmin(np.linalg.norm(diffs, axis=1)))]
                    _add(nearest, int(idx))
                    union(ci, cj)
                    break

    # ── Row-standardize ───────────────────────────────────────────────────────
    try:
        w.transform = "r"
    except Exception:
        for i in list(w.neighbors.keys()):
            wt    = w.weights.get(i, [])
            total = sum(wt) or 1.0
            if total > 0:
                w.weights[i] = [x / total for x in wt]

    logger.info(f"[build_weights] N={w.n} | avg_neighbors={w.mean_neighbors:.2f}")
    return w


# ══════════════════════════════════════════════════════════════════════════════
# 6. NETWORKX ROAD GRAPH
#    ⚠ LOGIKA INTI — JANGAN UBAH
# ══════════════════════════════════════════════════════════════════════════════
def build_road_graph(roads: gpd.GeoDataFrame, skenario: str, intensity: float, cfg: Cfg):
    """Bangun NetworkX graph dari segmen jalan aktif (tidak ditutup bencana).
    Returns: (G, node_array, kdtree)
    """
    hc = cfg.hazard_col_map.get(skenario, skenario)
    n_rm = n_ok = 0
    edge_weights: Dict[Tuple[tuple, tuple], float] = {}

    hazard_vals = roads[hc].to_numpy() if hc in roads.columns else None
    geoms = roads.geometry.to_numpy()

    for idx, geom in enumerate(geoms):
        if geom is None or geom.is_empty:
            continue
        raw_hazard = int(hazard_vals[idx]) if hazard_vals is not None else 0
        if cfg.norm_haz(raw_hazard) * intensity >= cfg.impact_closure_threshold:
            n_rm += 1
            continue
        n_ok += 1
        lines = [geom] if geom.geom_type == "LineString" else list(geom.geoms)
        for line in lines:
            coords = list(line.coords)
            for i in range(len(coords) - 1):
                x1, y1 = coords[i]
                x2, y2 = coords[i + 1]
                u = (round(x1, 2), round(y1, 2))
                v = (round(x2, 2), round(y2, 2))
                sl = math.hypot(x2 - x1, y2 - y1)
                key = (u, v) if u <= v else (v, u)
                prev = edge_weights.get(key)
                if prev is None or sl < prev:
                    edge_weights[key] = sl
    G = nx.Graph()
    G.add_weighted_edges_from((u, v, w) for (u, v), w in edge_weights.items())
    nl = np.array(list(G.nodes())) if G.nodes() else np.empty((0, 2))
    tn = cKDTree(nl) if len(nl) else None
    logger.info(f"[build_road_graph] closed={n_rm}, ok={n_ok}")
    return G, nl, tn


def _snap(G, tn, nl, xy, max_snap: float = 300):
    """Snap koordinat XY ke node terdekat dalam graph."""
    if tn is None or len(nl) == 0:
        return None
    d, i = tn.query(xy, k=1)
    if (d if np.isscalar(d) else d[0]) > max_snap:
        return None
    nd = tuple(nl[i if np.isscalar(i) else i[0]])
    return nd if G.has_node(nd) else None


def apply_road_cuts_to_graph(G: nx.Graph, nl, tn, cut_roads: List[dict], cfg: Cfg):
    """
    Terapkan penutupan jalan dari input user ke NetworkX graph (in-place pada salinan).
    Setiap item di cut_roads dapat berupa:
      - {"edge_id": int}   → row index di edge_df asli
      - {"lat": float, "lng": float}  → koordinat titik yang di-snap ke edge terdekat

    Untuk endpoint /api/simulate — ini memodifikasi SALINAN graph, bukan global.
    """
    G_sim = G.copy()
    for item in cut_roads:
        # Prioritaskan x/y (UTM) yang sudah dikonversi di main.py
        if "x" in item and "y" in item:
            xy = [item["x"], item["y"]]
            # Snapping ke node terdekat dengan radius lebih luas (100m)
            node = _snap(G_sim, tn, nl, xy, max_snap=100)
            if node and G_sim.has_node(node):
                # Hapus semua edge yang terhubung ke node tersebut
                edges_to_remove = list(G_sim.edges(node))
                G_sim.remove_edges_from(edges_to_remove)
                logger.info(f"[apply_road_cuts] {len(edges_to_remove)} edge dihapus di node {node} (titik klik)")
        elif "edge_from" in item and "edge_to" in item:
            u = (round(item["edge_from"][0], 2), round(item["edge_from"][1], 2))
            v = (round(item["edge_to"][0],   2), round(item["edge_to"][1],   2))
            if G_sim.has_edge(u, v):
                G_sim.remove_edge(u, v)
                logger.info(f"[apply_road_cuts] edge spesifik ({u}→{v}) dihapus")
    return G_sim


# ══════════════════════════════════════════════════════════════════════════════
# 7. FILTER TES
#    ⚠ LOGIKA INTI — JANGAN UBAH
# ══════════════════════════════════════════════════════════════════════════════
def filter_tes(tes_raw: Dict[str, gpd.GeoDataFrame], skenario: str, cfg: Cfg):
    """Filter TES berdasarkan threshold hazard skenario.
    Returns: (tes_valid_gdf | None, stats_dict)
    """
    hc   = cfg.hazard_col_map.get(skenario, skenario)
    lst  = []
    stats: Dict[str, dict] = {}
    for kat, gk in tes_raw.items():
        n   = len(gk)
        gv  = (gk[gk[hc] < cfg.tes_hazard_threshold].copy()
               if hc in gk.columns else gk.copy())
        stats[kat] = {"total": n, "valid": len(gv)}
        if len(gv) > 0:
            gv["kategori"] = kat
            lst.append(gv)
    if not lst:
        logger.error(f"[filter_tes] Tidak ada TES valid untuk {skenario.upper()}")
        return None, stats
    tes_v = gpd.GeoDataFrame(pd.concat(lst, ignore_index=True), crs=cfg.target_crs)
    n_valid = sum(v["valid"] for v in stats.values())
    n_total = sum(v["total"] for v in stats.values())
    logger.info(f"[filter_tes] TES valid: {n_valid}/{n_total}")
    return tes_v, stats


# ══════════════════════════════════════════════════════════════════════════════
# 8. COMPUTE DISTANCES (Pandana / Dijkstra)
#    ⚠ LOGIKA INTI — JANGAN UBAH
# ══════════════════════════════════════════════════════════════════════════════
def compute_distances(
    gdf: gpd.GeoDataFrame,
    skenario: str,
    tes_v: Optional[gpd.GeoDataFrame],
    cfg: Cfg,
    intensity: float = 0.0,
    t_pen: Optional[float] = None,
    net=None,
    edge_df=None,
    G: Optional[nx.Graph] = None,
    nl=None,
    tn=None,
):
    """Hitung waktu tempuh (menit) dari setiap grid ke TES per kategori.
    MENGGUNAKAN: Optimized Multi-Source Dijkstra + Vectorized cKDTree
    """
    n  = len(gdf)
    if "cx" in gdf.columns and "cy" in gdf.columns:
        cx = gdf["cx"].values
        cy = gdf["cy"].values
    else:
        cx = gdf.geometry.centroid.x.values
        cy = gdf.geometry.centroid.y.values

    tp = t_pen if (t_pen and t_pen > 0) else cfg.unreachable_time

    # ── Path B: NetworkX Optimized (Multi-Source Dijkstra) ────────────────────
    logger.info(f"[compute_distances] NetworkX Multi-Source Dijkstra [{skenario}|{intensity:.2f}]")
    
    # 1. Vectorized Snap Grid Centroids ke Jaringan Jalan
    gnodes = np.array([None] * n, dtype=object)
    if tn is not None and len(nl) > 0:
        dists, idxs = tn.query(np.column_stack((cx, cy)), k=1)
        valid_mask = dists <= 300
        for i in range(n):
            if valid_mask[i]:
                idx = idxs[i] if np.isscalar(idxs[i]) else idxs[i][0]
                nd = tuple(nl[idx])
                if G.has_node(nd):
                    gnodes[i] = nd

    if tes_v is None or len(tes_v) == 0:
        tpk = {k: np.full(n, tp) for k in cfg.kategori_fac}
        return tpk, np.full(n, tp), gnodes.tolist(), \
               {k: np.ones(n, int) for k in cfg.kategori_fac}, np.zeros(n, int)

    # 2. Kelompokkan TES berdasarkan kategori dan Snap ke Jaringan Jalan
    tnpk: Dict[str, List] = {}
    for kat, sub in tes_v.groupby("kategori"):
        snapped_nodes = []
        for _, r in sub.iterrows():
            d, i = tn.query([r.geometry.x, r.geometry.y], k=1)
            d_val = d if np.isscalar(d) else d[0]
            if d_val <= 300:
                idx = i if np.isscalar(i) else i[0]
                nd = tuple(nl[idx])
                if G.has_node(nd):
                    snapped_nodes.append(nd)
        tnpk[kat] = list(set(snapped_nodes))

    # 3. Multi-Source Dijkstra (Satu kali per kategori fasilitas)
    tpk = {}
    for kat in cfg.kategori_fac:
        sources = tnpk.get(kat, [])
        arr = np.full(n, np.inf)
        if sources:
            # Dijkstra dari seluruh TES sekaligus untuk kategori ini
            try:
                lengths = nx.multi_source_dijkstra_path_length(G, sources, weight="weight")
                for gi, gnd in enumerate(gnodes):
                    if gnd is not None:
                        arr[gi] = lengths.get(gnd, np.inf)
            except Exception as e:
                logger.warning(f"[compute_distances] Dijkstra gagal untuk {kat}: {e}")
        
        t = arr / cfg.walking_speed_m_per_min
        tpk[kat] = np.where(np.isinf(t), tp, t)

    tm   = np.column_stack(list(tpk.values())).min(axis=1)
    iso  = {k: (tpk[k] >= tp).astype(int)  for k in cfg.kategori_fac}
    opsi = np.column_stack([(tpk[k] < tp).astype(int) for k in cfg.kategori_fac]).sum(axis=1)
    return tpk, tm, gnodes.tolist(), iso, opsi


def calc_t_max(tpk: dict, cfg: Cfg) -> float:
    """Hitung T_max dari rata-rata waktu tempuh yang valid (non-unreachable)."""
    all_t = []
    for arr in tpk.values():
        v = arr[(arr < cfg.unreachable_time * 0.9) & ~np.isinf(arr) & (arr > 0)]
        all_t.extend(v.tolist())
    if not all_t:
        logger.warning("[calc_t_max] Fallback T_max=60 mnt")
        return 60.0
    t_max = float(np.max(all_t))
    logger.info(f"[calc_t_max] T_max (maksimal)={t_max:.2f} mnt | T_penalty={3 * t_max:.2f} mnt")
    return t_max


# ══════════════════════════════════════════════════════════════════════════════
# 9. SIMULASI HAZARD
#    ⚠ LOGIKA INTI — JANGAN UBAH (plot dihapus sesuai aturan #2)
# ══════════════════════════════════════════════════════════════════════════════
def simulate_hazard(
    gdf: gpd.GeoDataFrame,
    roads: Optional[gpd.GeoDataFrame],
    tes_raw: Dict[str, gpd.GeoDataFrame],
    hazard_type: str,
    intensity: float,
    cfg: Cfg,
    rs: int = 42,
):
    """Simulasi dampak bencana pada grid, jalan, dan TES.
    Returns: (gdf_sim, roads_sim, tes_sim, mask_dampak)
    """
    n  = len(gdf)
    hc = cfg.indeks_bahaya.get(hazard_type)
    if hc and hc in gdf.columns:
        h     = gdf[hc].fillna(0).values.astype(float)
        denom = h.max() - h.min()
        p     = (h - h.min()) / denom if denom > 1e-10 else np.full(n, 0.5)
    else:
        p = np.full(n, 0.5)
        logger.warning(f"[simulate_hazard] '{hc}' tidak ada → p=0.5")

    mask = (
        np.zeros(n, dtype=bool) if intensity == 0.0
        else (p >= (1.0 - intensity)) & (p > 0.0)
    )
    logger.info(
        f"[simulate_hazard] {mask.sum()}/{n} grid terdampak "
        f"({mask.sum() / n * 100:.1f}%) | intensity={intensity}"
    )

    gdf_s                               = gdf.copy(deep=False)
    gdf_s[f"sim_prob_{hazard_type}"]    = p
    gdf_s[f"sim_dampak_{hazard_type}"]  = mask.astype(int)
    tes_s   = {k: v.copy() for k, v in tes_raw.items()}
    roads_s = roads.copy(deep=False) if roads is not None else None

    # ── Tandai TES yang terdampak sebagai tidak valid ─────────────────────────
    if intensity > 0.0 and mask.any():
        hcr = cfg.hazard_col_map.get(hazard_type, hazard_type)
        impacted_geom = gdf_s[mask].geometry
        # Menggunakan sindex untuk pencarian spasial yang lebih cepat (tanpa unary_union)
        sindex = impacted_geom.sindex
        for kat, gt in tes_s.items():
            if hcr not in gt.columns:
                gt[hcr] = 0
            for idx in gt.index:
                pt = gt.at[idx, "geometry"]
                if pt and not pt.is_empty:
                    # Buffer 50m di sekitar TES point (hanya polygon kecil)
                    pt_buf = pt.buffer(50)
                    # Filter grid terdampak yang bounding box-nya berpotongan dengan buffer TES
                    possible_matches_idx = list(sindex.intersection(pt_buf.bounds))
                    if possible_matches_idx:
                        possible_matches = impacted_geom.iloc[possible_matches_idx]
                        precise_matches = possible_matches[possible_matches.intersects(pt_buf)]
                        if not precise_matches.empty:
                            if int(gt.at[idx, hcr]) < cfg.tes_hazard_threshold:
                                gt.at[idx, hcr] = cfg.road_break_threshold

    return gdf_s, roads_s, tes_s, mask


# ══════════════════════════════════════════════════════════════════════════════
# 10. PREPROCESSING & FEATURE ENGINEERING
#     ⚠ LOGIKA INTI — JANGAN UBAH (PowerTransformer → RobustScaler → PCA)
# ══════════════════════════════════════════════════════════════════════════════
def preprocess(
    gdf: gpd.GeoDataFrame,
    skenario: str,
    sk: str,
    cfg: Cfg,
    mask_dampak=None,
) -> np.ndarray:
    """Feature engineering: PowerTransformer → RobustScaler → PCA (95% var).
    Returns: X_pca (np.ndarray, shape [n_grid, n_components])
    """
    df     = pd.DataFrame(index=gdf.index)
    cb     = cfg.indeks_bahaya[skenario]
    if cb in gdf.columns:
        df[cb] = gdf[cb].fillna(0)
    for col in cfg.variabel_dasar:
        if col in gdf.columns:
            df[col] = gdf[col].fillna(gdf[col].median())

    final = [c for c in cfg.variabel_dasar + [cb] if c in df.columns]
    for kat in cfg.kategori_fac:
        for nc in [f"waktu_tes_{kat}_{sk}", f"waktu_tes_{kat}_{skenario}"]:
            if nc in gdf.columns:
                df[nc] = gdf[nc].fillna(cfg.unreachable_time).values
                final.append(nc)
                break
    oc = f"jumlah_opsi_rute_{sk}"
    if oc in gdf.columns:
        df[oc] = gdf[oc].fillna(0).values
        final.append(oc)

    X = df[final].copy().astype(float).values
    pipe = Pipeline([
        ("power",  PowerTransformer(method="yeo-johnson", standardize=True)),
        ("scaler", RobustScaler()),
        ("pca",    PCA(n_components=0.95, random_state=42)),
    ])
    X_pca = pipe.fit_transform(X)
    var   = pipe.named_steps["pca"].explained_variance_ratio_.cumsum()[-1]
    logger.info(
        f"[preprocess] {X.shape[1]} fitur → {X_pca.shape[1]} komponen PCA "
        f"({var * 100:.1f}% variance) | skenario={skenario} sk={sk}"
    )
    return X_pca


# ══════════════════════════════════════════════════════════════════════════════
# 11. K OPTIMAL (ELBOW METHOD)
#     ⚠ LOGIKA INTI — JANGAN UBAH
# ══════════════════════════════════════════════════════════════════════════════
def determine_k(X_pca: np.ndarray, skenario: str, cfg: Cfg) -> int:
    """Tentukan K optimal via elbow method (KneeLocator / heuristik).
    Returns: k_optimal (int)
    """
    ks       = list(cfg.k_range)
    inertias = []
    for k in tqdm(ks, desc="  Elbow", leave=False):
        try:
            km = KMeans(n_clusters=k, random_state=42,
                        n_init=cfg.elbow_n_init, max_iter=cfg.elbow_max_iter)
            km.fit(X_pca)
            inertias.append(km.inertia_)
        except Exception as e:
            logger.warning(f"[determine_k] k={k} gagal: {e}")
            inertias.append(np.nan)

    ia      = np.array(inertias)
    valid_k = [ks[i] for i in range(len(ks)) if not np.isnan(ia[i])]
    valid_i = ia[~np.isnan(ia)]

    if len(valid_k) < 2:
        return 4

    k_opt = None

    if KNEED_OK:
        try:
            kl    = KneeLocator(valid_k, valid_i, curve="convex", direction="decreasing",
                                interp_method="interp1d")
            k_opt = kl.knee
            if k_opt is not None:
                k_opt = int(k_opt)
                logger.info(f"[determine_k] [{skenario}] K={k_opt} (KneeLocator)")
        except Exception as e:
            logger.warning(f"[determine_k] KneeLocator gagal: {e}")
            k_opt = None

    if k_opt is None:
        # Heuristik: relative difference
        diffs = np.abs(np.diff(valid_i)) / (np.array(valid_i[:-1]) + 1e-10)
        if len(diffs) > 0:
            k_opt = valid_k[int(np.argmax(diffs)) + 1]
            logger.info(f"[determine_k] [{skenario}] K={k_opt} (heuristik relative diff)")
        else:
            k_opt = 4

    # Parsimony fallback
    if k_opt is not None and k_opt <= cfg.k_min_parsimony:
        logger.warning(f"[determine_k] K={k_opt} terlalu kecil, hitung ulang subset K>=3")
        subset_mask = np.array(valid_k) >= 3
        subset_k = np.array(valid_k)[subset_mask]
        subset_i = np.array(valid_i)[subset_mask]
        
        if len(subset_k) >= 2:
            subset_diffs = np.abs(np.diff(subset_i)) / subset_i[:-1]
            k_opt = subset_k[int(np.argmax(subset_diffs)) + 1]
            logger.info(f"[determine_k] [{skenario}] K={k_opt} (Parsimony fallback relative diff)")
        else:
            k_opt = 3

    return k_opt


# ══════════════════════════════════════════════════════════════════════════════
# 12. NUMBA HELPERS (REDCAP)
#     ⚠ LOGIKA INTI — JANGAN UBAH
# ══════════════════════════════════════════════════════════════════════════════
@jit(nopython=True)
def _redcap_ward(Xa, Xb):
    na = Xa.shape[0]; nb = Xb.shape[0]
    if na == 0 or nb == 0: return 0.0
    p = Xa.shape[1]; ma = np.zeros(p); mb = np.zeros(p)
    for j in range(p):
        for i in range(na): ma[j] += Xa[i, j]
        ma[j] /= na
        for i in range(nb): mb[j] += Xb[i, j]
        mb[j] /= nb
    s = 0.0
    for j in range(p): d = ma[j] - mb[j]; s += d * d
    return float(na * nb) / float(na + nb) * s


@jit(nopython=True)
def _redcap_single(Xa, Xb):
    md = 1e18
    for i in range(Xa.shape[0]):
        for j in range(Xb.shape[0]):
            d = 0.0
            for k in range(Xa.shape[1]): diff = Xa[i, k] - Xb[j, k]; d += diff * diff
            if d ** 0.5 < md: md = d ** 0.5
    return md


@jit(nopython=True)
def _redcap_complete(Xa, Xb):
    md = 0.0
    for i in range(Xa.shape[0]):
        for j in range(Xb.shape[0]):
            d = 0.0
            for k in range(Xa.shape[1]): diff = Xa[i, k] - Xb[j, k]; d += diff * diff
            if d ** 0.5 > md: md = d ** 0.5
    return md


def _euc(xa, xb):
    s = 0.0
    for i in range(xa.shape[0]): d = xa[i] - xb[i]; s += d * d
    return s ** 0.5


# ══════════════════════════════════════════════════════════════════════════════
# 13. ALGORITMA CLUSTERING
#     ⚠ LOGIKA INTI — JANGAN UBAH SAMA SEKALI
# ══════════════════════════════════════════════════════════════════════════════

class SpatialDistanceWeightedFCM:
    """
    Spatial Distance-Weighted Fuzzy C-Means (SDWFCM) — Algoritma Utama.
    Menggabungkan jarak fitur (da) dan jarak spasial berbobot KNN-Gaussian (ds)
    dalam fungsi membership fuzzy.
    ⚠ LOGIKA MATEMATIKA TIDAK DIUBAH — hanya tqdm dipindah ke logger.
    """
    def __init__(self, k=5, m=1.7, alpha=0.5, sigma=None, knn=8,
                 max_iter=150, tol=1e-4, rs=42):
        self.k = k; self.m = m; self.alpha = alpha; self.sigma = sigma
        self.knn = knn; self.max_iter = max_iter; self.tol = tol; self.rs = rs
        self.labels_ = self.U_ = self.max_membership_ = self.centers_ = None

    def _build_W(self, gdf_or_coords):
        if hasattr(gdf_or_coords, "columns") and "cx" in gdf_or_coords.columns and "cy" in gdf_or_coords.columns:
            coords = np.column_stack([gdf_or_coords["cx"].values, gdf_or_coords["cy"].values])
        elif hasattr(gdf_or_coords, "geometry"):
            coords = np.column_stack([
                gdf_or_coords.geometry.centroid.x.values,
                gdf_or_coords.geometry.centroid.y.values,
            ])
        else:
            coords = np.asarray(gdf_or_coords)
        cache_key = (
            int(coords.shape[0]),
            int(self.knn),
            float(coords[0, 0]),
            float(coords[0, 1]),
            float(coords[-1, 0]),
            float(coords[-1, 1]),
        )
        cached_W = _SDWFCM_W_CACHE.get(cache_key)
        if cached_W is not None:
            self._sigma = _SDWFCM_SIGMA_CACHE[cache_key]
            return cached_W
        n  = len(coords)
        nn = NearestNeighbors(n_neighbors=min(self.knn + 1, n),
                              algorithm="ball_tree", n_jobs=-1)
        nn.fit(coords)
        dists, idxs = nn.kneighbors(coords)
        sigma = self.sigma or float(np.median(dists[:, 1:]))
        self._sigma = sigma
        rows, cols, data = [], [], []
        for i in range(n):
            nb = idxs[i, 1:]; nd = dists[i, 1:]
            w  = np.exp(-nd ** 2 / (2 * sigma ** 2))
            w /= (w.sum() + 1e-10)
            for jp, j in enumerate(nb):
                rows.append(i); cols.append(int(j)); data.append(float(w[jp]))
        W = csr_matrix((data, (rows, cols)), shape=(n, n), dtype=np.float64)
        _SDWFCM_W_CACHE[cache_key] = W
        _SDWFCM_SIGMA_CACHE[cache_key] = sigma
        return W

    def fit(self, X, gdf_or_coords, mask_dampak=None):
        np.random.seed(self.rs)
        n, _ = X.shape; k = self.k; m = self.m
        W  = self._build_W(gdf_or_coords)
        dw = np.ones(n)
        if mask_dampak is not None and mask_dampak.any():
            dw[mask_dampak] = 2.0
        D = sp.diags(dw, format="csr")
        U = np.random.dirichlet(np.ones(k), size=n)
        for it in range(self.max_iter):
            Um      = U ** m
            centers = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
            da      = cdist(X, centers) ** 2 + 1e-10
            We      = W @ D
            ds      = np.zeros((n, k))
            for ci in range(k):
                ds[:, ci] = (
                    (We @ (da[:, ci] * Um[:, ci]))
                    / ((W @ Um[:, ci]) + 1e-10)
                )
            dt  = np.clip((1 - self.alpha) * da + self.alpha * ds, 1e-10, None)
            exp = 2 / (m - 1)
            r   = dt[:, :, None] / dt[:, None, :]
            Un  = 1 / (r ** exp).sum(axis=2)
            Un  = np.clip(Un, 1e-10, None)
            Un /= Un.sum(axis=1, keepdims=True)
            diff = np.linalg.norm(Un - U)
            U    = Un
            if diff < self.tol:
                logger.info(f"[SDWFCM] konvergen pada iterasi {it} | diff={diff:.6f}")
                break
        self.U_               = U
        self.labels_          = np.argmax(U, axis=1)
        self.max_membership_  = U.max(axis=1)
        self.centers_         = centers
        logger.info(f"[SDWFCM] {len(set(self.labels_))} klaster | σ={self._sigma:.2f}")
        return self


class SpatialFuzzyCMeans:
    """
    Spatial Fuzzy C-Means (SFCM) — Pembanding 1.
    Memodifikasi jarak FCM standar dengan lag spasial dari bobot ketetanggaan (W).
    ⚠ LOGIKA MATEMATIKA TIDAK DIUBAH.
    """
    def __init__(self, k=5, m=2.0, alpha=0.5, max_iter=150, tol=1e-4, rs=42):
        self.k = k; self.m = m; self.alpha = alpha
        self.max_iter = max_iter; self.tol = tol; self.rs = rs
        self.labels_ = self.U_ = self.max_membership_ = None

    def fit(self, X, w):
        np.random.seed(self.rs)
        n, _ = X.shape; k = self.k; m = self.m
        adj = [list(w.neighbors.get(i, [])) for i in range(n)]
        U   = np.random.dirichlet(np.ones(k), size=n)
        for it in range(self.max_iter):
            Um      = U ** m
            centers = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
            da      = cdist(X, centers) ** 2 + 1e-10
            Us      = np.array([
                U[adj[i]].mean(0) if adj[i] else U[i]
                for i in range(n)
            ])
            ds = np.zeros((n, k))
            for ci in range(k):
                dnb = np.sum((X - centers[ci]) ** 2, axis=1) + 1e-10
                for i in range(n):
                    ds[i, ci] = (
                        (np.mean(dnb[adj[i]]) * Us[i, ci])
                        if adj[i] else da[i, ci]
                    )
            dt  = np.clip((1 - self.alpha) * da + self.alpha * ds, 1e-10, None)
            exp = 2 / (m - 1)
            Un  = np.zeros_like(U)
            for ci in range(k):
                Un[:, ci] = 1 / ((dt[:, ci:ci + 1] / dt).sum(axis=1) ** exp)
            Un   = np.clip(Un, 1e-10, None)
            Un  /= Un.sum(axis=1, keepdims=True)
            diff = np.linalg.norm(Un - U)
            U    = Un
            if diff < self.tol:
                logger.info(f"[SFCM] konvergen pada iterasi {it} | diff={diff:.6f}")
                break
        self.U_              = U
        self.labels_         = np.argmax(U, axis=1)
        self.max_membership_ = U.max(axis=1)
        logger.info(f"[SFCM] {len(set(self.labels_))} klaster")
        return self


class REDCAPManual:
    """
    REDCAP — Pembanding 2.
    Penggabungan hirarki berbasis MST dengan kendala kontiguitas spasial.
    ⚠ LOGIKA MATEMATIKA TIDAK DIUBAH.
    """
    def __init__(self, X, w, k=5, linkage="ward", size_alpha=1.0,
                 net_dist=None, iso_pen=10.0, iso_thr=30.0):
        self.X = X; self.w = w; self.k = k; self.linkage = linkage
        self.size_alpha = size_alpha; self.net_dist = net_dist
        self.iso_pen = iso_pen; self.iso_thr = iso_thr
        self.labels_ = None; self.n = X.shape[0]

    def _mst(self):
        G = nx.Graph()
        G.add_nodes_from(range(self.n))
        for i in range(self.n):
            for j in self.w.neighbors[i]:
                if i < j:
                    G.add_edge(i, j, weight=float(_euc(self.X[i], self.X[j])))
        if not nx.is_connected(G):
            for c1, c2 in zip(list(nx.connected_components(G))[:-1],
                               list(nx.connected_components(G))[1:]):
                c1, c2 = list(c1), list(c2)
                bd, bu, bv = np.inf, c1[0], c2[0]
                for u in c1:
                    for v in c2:
                        d = float(_euc(self.X[u], self.X[v]))
                        if d < bd: bd, bu, bv = d, u, v
                G.add_edge(bu, bv, weight=bd)
        return nx.minimum_spanning_tree(G, weight="weight")

    def _iso(self, ma, mb):
        if self.net_dist is None: return 1.0
        ai = float(self.net_dist[list(ma)].mean()) > self.iso_thr
        bi = float(self.net_dist[list(mb)].mean()) > self.iso_thr
        return self.iso_pen if ai != bi else 1.0

    def _diss(self, ma, mb):
        Xa = self.X[list(ma)]; Xb = self.X[list(mb)]
        if NUMBA_OK:
            if self.linkage == "single":   return float(_redcap_single(Xa, Xb))
            if self.linkage == "complete": return float(_redcap_complete(Xa, Xb))
            if self.linkage == "average":  return float(cdist(Xa, Xb).mean())
            return float(_redcap_ward(Xa, Xb))
        if self.linkage == "single":   return float(cdist(Xa, Xb).min())
        if self.linkage == "complete": return float(cdist(Xa, Xb).max())
        if self.linkage == "average":  return float(cdist(Xa, Xb).mean())
        na, nb = len(ma), len(mb)
        return float((na * nb) / (na + nb) * np.sum((Xa.mean(0) - Xb.mean(0)) ** 2))

    def _full_diss(self, ma, mb): return self._diss(ma, mb) * self._iso(ma, mb)
    def _pen(self, d, n): return d * (n ** self.size_alpha)

    def _adj(self, ma, mb):
        return any(j in mb for i in ma for j in self.w.neighbors[i])

    def _rebuild(self, regs, sz, u2r, dc):
        dc.clear(); heap = []; seen = set()
        for ra, ma in regs.items():
            for rb in {u2r[j] for i in ma
                       for j in self.w.neighbors[i]
                       if u2r[j] != ra and u2r[j] in regs}:
                key = (min(ra, rb), max(ra, rb))
                if key in seen or not self._adj(regs[ra], regs[rb]): continue
                seen.add(key)
                d = self._full_diss(regs[ra], regs[rb]); dc[key] = d
                heapq.heappush(heap, (self._pen(d, sz[ra] + sz[rb]), ra, rb))
        return heap

    def solve(self):
        logger.info("[REDCAP] REDCAP solve...")
        mst   = self._mst()
        regs  = {i: {i}  for i in range(self.n)}
        sz    = {i: 1    for i in range(self.n)}
        u2r   = {i: i    for i in range(self.n)}
        dc    = {}; heap = []
        for u, v in mst.edges():
            ra, rb = u2r[u], u2r[v]
            if ra != rb:
                key = (min(ra, rb), max(ra, rb))
                if not self._adj(regs[ra], regs[rb]): continue
                d = self._full_diss(regs[ra], regs[rb])
                if key not in dc or d < dc[key]:
                    dc[key] = d
                    heapq.heappush(heap, (self._pen(d, sz[ra] + sz[rb]), ra, rb))
        nr  = self.n; tgt = self.k
        while nr > tgt:
            merged = False
            while heap:
                dh, ra, rb = heapq.heappop(heap)
                if ra not in regs or rb not in regs: continue
                key = (min(ra, rb), max(ra, rb))
                if key not in dc: continue
                if abs(dh - self._pen(dc[key], sz[ra] + sz[rb])) > 1e-12: continue
                if not self._adj(regs[ra], regs[rb]):
                    dc.pop(key, None); continue
                nm = regs[ra] | regs[rb]; ns = sz[ra] + sz[rb]
                for u in regs[rb]: u2r[u] = ra
                regs[ra] = nm; sz[ra] = ns
                del regs[rb], sz[rb]; dc.pop(key, None)
                nr -= 1; merged = True
                for rb2 in {u2r[j] for i in nm
                             for j in self.w.neighbors[i]
                             if u2r[j] != ra and u2r[j] in regs}:
                    if not self._adj(regs[ra], regs[rb2]): continue
                    nk = (min(ra, rb2), max(ra, rb2))
                    d2 = self._full_diss(regs[ra], regs[rb2])
                    dc[nk] = d2
                    heapq.heappush(heap, (self._pen(d2, sz[ra] + sz[rb2]), ra, rb2))
                break
            if not merged:
                heap = self._rebuild(regs, sz, u2r, dc)
                if heap: continue
                # Bridge fallback
                ri = list(regs.keys())
                rc = np.array([self.X[list(regs[r])].mean(0) for r in ri])
                tr = cKDTree(rc); bp = None
                for qi, r_i in enumerate(ri):
                    _, ids = tr.query(rc[qi], k=min(5, len(ri)))
                    for idx in ids[1:]:
                        if ri[int(idx)] != r_i: bp = (r_i, ri[int(idx)]); break
                    if bp: break
                if bp is None: break
                ra2, rb2 = bp
                ua, ub = list(regs[ra2])[0], list(regs[rb2])[0]
                for a, b in [(ua, ub), (ub, ua)]:
                    self.w.neighbors[a] = list(self.w.neighbors.get(a, [])) + [b]
                    self.w.weights[a]   = list(self.w.weights.get(a, []))   + [1.0]
                heap = self._rebuild(regs, sz, u2r, dc)
                if not heap: break
        lmap = {rid: i for i, rid in enumerate(sorted(regs))}
        labs = np.zeros(self.n, int)
        for rid, m in regs.items():
            for u in m: labs[u] = lmap[rid]
        uniq = np.unique(labs)
        self.labels_ = np.array([{o: nv for nv, o in enumerate(uniq)}[l]
                                  for l in labs])
        logger.info(f"[REDCAP] {len(np.unique(self.labels_))} klaster")


def run_skater(gdf: gpd.GeoDataFrame, w, X_pca: np.ndarray, k: int, cfg: Cfg) -> np.ndarray:
    """
    SKATER — Pembanding 3.
    MST + edge removal. Menggunakan spopt.region.Skater jika tersedia.
    ⚠ LOGIKA INTI — JANGAN UBAH.
    """
    if SKATER_OK:
        try:
            skater = Skater(gdf, w, attrs_name=None, n_clusters=k,
                            min_region=cfg.skater_min_region)
            skater.solve()
            labs = np.array(skater.labels_)
            logger.info(f"[SKATER] spopt: {len(np.unique(labs))} klaster")
            return labs
        except Exception as e:
            logger.warning(f"[SKATER] spopt gagal ({e}), pakai fallback manual")

    # ── Fallback manual: MST edge removal ────────────────────────────────────
    n = len(X_pca)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for i in range(n):
        for j in w.neighbors.get(i, []):
            if i < j:
                dist = float(np.linalg.norm(X_pca[i] - X_pca[j]))
                G.add_edge(i, j, weight=dist)
    if not nx.is_connected(G):
        comps = list(nx.connected_components(G))
        for c1, c2 in zip(comps[:-1], comps[1:]):
            c1, c2 = list(c1), list(c2)
            best_d, bu, bv = np.inf, c1[0], c2[0]
            for u in c1:
                for v in c2:
                    d = float(np.linalg.norm(X_pca[u] - X_pca[v]))
                    if d < best_d: best_d, bu, bv = d, u, v
            G.add_edge(bu, bv, weight=best_d)
    mst   = nx.minimum_spanning_tree(G, weight="weight")
    edges = sorted(mst.edges(data=True), key=lambda e: e[2]["weight"], reverse=True)
    for u, v, _ in edges[:k - 1]:
        mst.remove_edge(u, v)
    comps = list(nx.connected_components(mst))
    labs  = np.zeros(n, int)
    for ci, comp in enumerate(comps):
        for node in comp: labs[node] = ci
    logger.info(f"[SKATER] manual: {len(np.unique(labs))} klaster")
    return labs


# ══════════════════════════════════════════════════════════════════════════════
# 14. CLUSTERING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
def _run(name: str, fn):
    """Wrapper aman untuk menjalankan satu algoritma clustering."""
    logger.info(f"[_run] {name} dimulai...")
    t0 = time.time()
    try:
        r    = fn()
        t    = time.time() - t0
        labs = r if isinstance(r, np.ndarray) else r.get("labels")
        nc   = len(set(labs[labs >= 0])) if labs is not None else 0
        logger.info(f"[_run] {name} selesai {t:.1f}s → {nc} klaster")
        if isinstance(r, np.ndarray):
            return {"labels": r, "time": t}
        r["time"] = t
        return r
    except Exception as e:
        logger.error(f"[_run] {name} gagal: {e}")
        return None


def run_all_clustering(
    gdf: gpd.GeoDataFrame,
    w,
    X_pca: np.ndarray,
    k: int,
    skenario: str,
    cfg: Cfg,
    mask_dampak=None,
    fast_mode: bool = False,
) -> Dict[str, Optional[dict]]:
    """Jalankan semua algoritma clustering.
    Returns: dict {"SDWFCM": {...}, "SFCM": {...}, "REDCAP": {...}, "SKATER": {...}}
    """
    logger.info(f"[run_all_clustering] [{skenario.upper()}] K={k}")
    nda = (gdf[f"waktu_tes_min_{skenario}"].values
           if f"waktu_tes_min_{skenario}" in gdf.columns else None)
    results = {}

    sdwfcm_max_iter = min(cfg.sdwfcm_max_iter, 30) if fast_mode else cfg.sdwfcm_max_iter
    sdwfcm_tol = max(cfg.sdwfcm_tol, 2e-3) if fast_mode else cfg.sdwfcm_tol

    def _sdwfcm():
        m = SpatialDistanceWeightedFCM(
            k=k, m=cfg.sdwfcm_m, alpha=cfg.sdwfcm_alpha,
            sigma=cfg.sdwfcm_sigma, knn=cfg.sdwfcm_knn,
            max_iter=sdwfcm_max_iter, tol=sdwfcm_tol, rs=42,
        ).fit(X_pca, gdf, mask_dampak=mask_dampak)
        return {"labels": m.labels_, "U": m.U_,
                "max_membership": m.max_membership_,
                "centers": m.centers_, "sigma": m._sigma}

    def _sfcm():
        m = SpatialFuzzyCMeans(
            k=k, m=cfg.sfcm_m, alpha=cfg.sfcm_alpha,
            max_iter=cfg.sfcm_max_iter, tol=cfg.sfcm_tol, rs=42,
        ).fit(X_pca, w)
        return {"labels": m.labels_, "U": m.U_,
                "max_membership": m.max_membership_}

    def _redcap():
        m = REDCAPManual(
            X_pca, w, k=k, linkage=cfg.redcap_linkage,
            size_alpha=cfg.size_alpha, net_dist=nda,
            iso_pen=cfg.isolation_penalty_weight,
            iso_thr=cfg.isolation_time_threshold,
        )
        m.solve()
        return m.labels_

    def _skater():
        return run_skater(gdf, w, X_pca, k, cfg)

    # HANYA JALANKAN SDWFCM AGAR API WEB MERESPONS DALAM < 10 DETIK
    for name, fn in [("SDWFCM", _sdwfcm)]:
        r = _run(name, fn)
        if r:
            results[name] = r

    logger.info(f"[run_all_clustering] {len(results)}/4 algoritma berhasil")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# 15. EVALUASI MODEL
# ══════════════════════════════════════════════════════════════════════════════
def _size_entropy(labs: np.ndarray) -> float:
    lv = labs[labs >= 0]
    if len(lv) == 0: return 0.0
    sz = pd.Series(lv).value_counts(); p = sz / sz.sum()
    return float(-(p * np.log(p + 1e-10)).sum())


def eval_one(X_pca, res, gdf, w, algo: str, skenario: str, cfg: Cfg) -> dict:
    """Evaluasi satu algoritma: Silhouette, Davies-Bouldin, Calinski-Harabasz, Moran."""
    labs = res.get("labels") if isinstance(res, dict) else res
    if labs is None:
        return {"algoritma": algo, "error": "no labels"}
    lv = labs[labs >= 0]
    if len(set(lv)) < 2:
        return {"algoritma": algo, "error": "<2 cluster"}
    m  = {"algoritma": algo, "n_cluster": len(set(lv)),
          "n_noise": int((labs == -1).sum())}
    Xv = X_pca[labs >= 0]; Lv = labs[labs >= 0]
    for fn, key in [(silhouette_score,         "silhouette"),
                    (calinski_harabasz_score,   "calinski_harabasz"),
                    (davies_bouldin_score,      "davies_bouldin")]:
        try:    m[key] = round(fn(Xv, Lv), 4)
        except: m[key] = float("nan")
    try:
        y = np.array(np.where(labs < 0, 0, labs), dtype=np.float64)
        if len(y) == w.n:
            mi = Moran(y, w, permutations=99)
            m["moran_cluster"] = round(mi.I, 4)
            m["moran_p"]       = round(mi.p_sim, 4)
        else:
            m["moran_cluster"] = m["moran_p"] = float("nan")
    except Exception:
        m["moran_cluster"] = m["moran_p"] = float("nan")
    m["size_entropy"] = round(_size_entropy(labs), 4)
    nc = f"waktu_tes_min_{skenario}"
    if nc in gdf.columns:
        nd  = gdf[nc].values
        m["waktu_tes_mean"] = round(
            float(np.array([nd[labs == c].mean() for c in np.unique(lv)]).mean()), 1
        )
    mm = res.get("max_membership") if isinstance(res, dict) else None
    if mm is not None:
        m["ambig_pct"]       = round(float((mm < 0.6).sum() / len(mm) * 100), 2)
        m["membership_mean"] = round(float(np.mean(mm)), 4)
    return m


def evaluate_all(results: dict, X_pca, gdf, w, k: int, skenario: str, cfg: Cfg) -> pd.DataFrame:
    """Evaluasi semua algoritma, kembalikan DataFrame metrik."""
    rows = [eval_one(X_pca, res, gdf, w, algo, skenario, cfg)
            for algo, res in results.items()]
    df   = pd.DataFrame(rows)
    logger.info(f"[evaluate_all] selesai | {len(df)} baris")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 16. DETEKSI TITIK AMAN SEMU
#     ⚠ LOGIKA INTI — JANGAN UBAH (plot & to_file dihapus sesuai aturan #2 #3)
# ══════════════════════════════════════════════════════════════════════════════
def detect_titik_aman_semu(
    gdf_sim: gpd.GeoDataFrame,
    labels: np.ndarray,
    skenario: str,
    sk: str,
    cfg: Cfg,
    baseline_times: Optional[np.ndarray] = None,
    psi_array: Optional[np.ndarray] = None,
    t_pen: float = 9999.0,
    is_isolated_override: Optional[np.ndarray] = None,
) -> gpd.GeoDataFrame:
    """
    Identifikasi grid yang termasuk 'Titik Aman Semu' (Hybrid Academic Logic):
    pseudo_safe = (PSI >= threshold) AND (ALR >= threshold)
    """
    # Kolom waktu tempuh saat ini (tanpa prefix intensitas agar konsisten)
    tc = f"waktu_tes_min_{skenario}" 
    if tc not in gdf_sim.columns:
        logger.warning(f"[detect_titik_aman_semu] kolom {tc} tidak ada")
        return gpd.GeoDataFrame()

    # T_current
    tm_curr = gdf_sim[tc].fillna(cfg.unreachable_time).values
    
    # 1. Identifikasi Isolasi (Connectivity Failure)
    # Jalur komputasi penuh memakai ambang penalty; jalur cache boleh memberi
    # mask eksplisit agar grid reachable yang waktunya mendekati penalty tidak
    # salah diberi status isolated.
    if is_isolated_override is not None:
        is_isolated = np.asarray(is_isolated_override, dtype=bool)
    else:
        is_isolated = (tm_curr >= t_pen * 0.98)
    
    # 2. Ambil PSI (Intrinsic Instability)
    if psi_array is None:
        psi_col = f"PSI_{skenario}"
        if psi_col in gdf_sim.columns:
            psi_array = gdf_sim[psi_col].values
        else:
            # Tetap buat kolom agar tidak error di frontend
            gdf_sim["psi_val"] = 0.0
            gdf_sim["alr_val"] = np.where(is_isolated, np.nan, 0.0)
            gdf_sim["is_isolated"] = is_isolated.astype(bool)
            gdf_sim["is_semu"] = 0
            return gpd.GeoDataFrame()
    
    # 3. Ambil Baseline Times & Hitung ALR (Accessibility Loss Ratio)
    if baseline_times is None:
        gdf_sim["psi_val"] = psi_array
        gdf_sim["alr_val"] = np.where(is_isolated, np.nan, 0.0)
        gdf_sim["is_isolated"] = is_isolated.astype(bool)
        gdf_sim["is_semu"] = 0
        return gpd.GeoDataFrame()
    
    # ALR = (T_current - T_baseline) / T_baseline (Murni Matematis)
    t_base = np.where(baseline_times <= 0, 1e-6, baseline_times)
    alr_raw = (tm_curr - baseline_times) / t_base
    
    # Jika terisolasi, ALR tidak terdefinisi secara rasio (set ke NaN untuk statistik)
    alr_final = np.where(is_isolated, np.nan, alr_raw)
    
    # Simpan metrik ke GDF (SELALU simpan agar muncul di popup)
    gdf_sim["psi_val"] = psi_array
    gdf_sim["alr_val"] = alr_final
    gdf_sim["is_isolated"] = is_isolated.astype(bool)
    
    # 3. Filter Final (Logika Akademik)
    # Area Aman Semu = Fragile (PSI tinggi) DAN (Isolated ATAU ALR Severe)
    mask_semu = (psi_array >= cfg.psi_threshold_fragile) & (is_isolated | (alr_raw >= cfg.alr_threshold_severe))
    gdf_sim["is_semu"] = mask_semu.astype(int)

    n_semu = int(mask_semu.sum())
    n_iso  = int(is_isolated.sum())
    logger.info(
        f"[detect_titik_aman_semu] PSI >= {cfg.psi_threshold_fragile} & "
        f"(Iso={n_iso} | ALR >= {cfg.alr_threshold_severe}) -> semu={n_semu}"
    )

    if n_semu == 0:
        return gpd.GeoDataFrame()
        
    gdf_s               = gdf_sim[mask_semu].copy()
    gdf_s["_kategori"]  = "titik_aman_semu"
    gdf_s["_cluster"]   = labels[mask_semu]
    return gdf_s


# ══════════════════════════════════════════════════════════════════════════════
# 17. ROUTE SINGLE POINT (untuk endpoint /api/route)
#     Fungsi BARU — menggabungkan logika Dijkstra + path reconstruction
# ══════════════════════════════════════════════════════════════════════════════
def route_to_nearest_tes(
    origin_x: float,
    origin_y: float,
    tes_v: Optional[gpd.GeoDataFrame],
    cfg: Cfg,
    G: Optional[nx.Graph] = None,
    nl=None,
    tn=None,
    net=None,
    edge_df=None,
    skenario: str = "banjir",
    intensity: float = 0.0,
    t_pen: Optional[float] = None,
    kategori_filter: Optional[str] = None,
) -> dict:
    """
    Hitung rute terpendek dari satu titik asal (klik user) ke TES terdekat.

    Args:
        kategori_filter: Jika diisi (misal "kesehatan"), hanya cari TES dari
                         kategori tersebut saja. Jika None, cari semua kategori.
    Returns dict:
      {
        "found": bool,
        "travel_time_min": float,
        "distance_m": float,
        "tes_kategori": str,
        "tes_coords": [x, y],
        "path_coords": [[x, y], ...],
        "geojson_linestring": {...}
      }
    """
    tp = t_pen if (t_pen and t_pen > 0) else cfg.unreachable_time
    result_base = {
        "found":            False,
        "travel_time_min":  tp,
        "distance_m":       None,
        "tes_kategori":     None,
        "tes_coords":       None,
        "path_coords":      None,
        "geojson_linestring": None,
    }

    # Filter berdasarkan kategori jika diminta
    if kategori_filter and tes_v is not None and "kategori" in tes_v.columns:
        tes_v = tes_v[tes_v["kategori"] == kategori_filter].copy()

    if tes_v is None or len(tes_v) == 0:
        logger.warning(f"[route_to_nearest_tes] Tidak ada TES valid" +
                       (f" (kategori={kategori_filter})" if kategori_filter else ""))
        return result_base

    if G is None or tn is None:
        # ── Fallback: jarak Euclidean langsung ke TES terdekat ────────────────
        logger.warning("[route_to_nearest_tes] Graph tidak tersedia → Euclidean fallback")
        best_d = np.inf; best_tes = None; best_kat = None
        for _, row in tes_v.iterrows():
            d = np.hypot(row.geometry.x - origin_x, row.geometry.y - origin_y)
            if d < best_d:
                best_d   = d
                best_tes = row.geometry
                best_kat = row.get("kategori", "unknown")
        if best_tes is None:
            return result_base
        t = best_d / cfg.walking_speed_m_per_min
        line = LineString([(origin_x, origin_y), (best_tes.x, best_tes.y)])
        return {
            "found":            True,
            "travel_time_min":  round(t, 2),
            "distance_m":       round(best_d, 1),
            "tes_kategori":     best_kat,
            "tes_coords":       [best_tes.x, best_tes.y],
            "path_coords":      [[origin_x, origin_y], [best_tes.x, best_tes.y]],
            "geojson_linestring": line.__geo_interface__,
        }

    # ── Snap origin ke graph ──────────────────────────────────────────────────
    origin_node = _snap(G, tn, nl, [origin_x, origin_y])
    if origin_node is None:
        logger.warning(f"[route_to_nearest_tes] Origin ({origin_x:.1f},{origin_y:.1f}) terlalu jauh dari jalan")
        return result_base

    # ── Snap semua TES ke graph, catat kategori & nama ────────────────────────
    tes_nodes: List[Tuple] = []
    tes_kat_map: Dict[Tuple, str] = {}
    tes_name_map: Dict[Tuple, str] = {}
    tes_geom_map: Dict[Tuple, Tuple] = {}
    
    # Prioritaskan kolom nama: 'Nama_Objek', 'nama', 'Nama', 'REMARK', 'Fasilitas', 'KETERANGAN', 'NAMA_UNSUR'
    name_cols = ["Nama_Objek", "nama", "Nama", "Name", "NAME", "REMARK", "Fasilitas", "KETERANGAN", "NAMA_UNSUR"]
    
    for _, row in tes_v.iterrows():
        nd = _snap(G, tn, nl, [row.geometry.x, row.geometry.y])
        if nd:
            tes_nodes.append(nd)
            tes_kat_map[nd]  = row.get("kategori", "unknown")
            tes_geom_map[nd] = (row.geometry.x, row.geometry.y)
            
            # Cari nama TES
            name = "Fasilitas TES"
            for c in name_cols:
                if c in row.index and pd.notna(row[c]):
                    name = str(row[c])
                    break
            tes_name_map[nd] = name

    if not tes_nodes:
        logger.warning("[route_to_nearest_tes] Tidak ada TES yang bisa di-snap ke graph")
        return result_base

    # ── Dijkstra dari origin ──────────────────────────────────────────────────
    try:
        lengths, paths = nx.single_source_dijkstra(G, origin_node, weight="weight")
    except Exception as e:
        logger.error(f"[route_to_nearest_tes] Dijkstra gagal: {e}")
        return result_base

    # ── Cari TES dengan jarak terpendek ──────────────────────────────────────
    best_d    = np.inf
    best_node = None
    for nd in tes_nodes:
        d = lengths.get(nd, np.inf)
        if d < best_d:
            best_d    = d
            best_node = nd

    if best_node is None or np.isinf(best_d):
        logger.warning("[route_to_nearest_tes] TES tidak dapat dijangkau dari titik asal")
        return result_base

    # ── Rekonstruksi path koordinat ──────────────────────────────────────────
    path_nodes  = paths.get(best_node, [])
    path_coords = [[float(n[0]), float(n[1])] for n in path_nodes]
    # Tambahkan origin dan destination tepat (bukan hanya node graph)
    if path_coords:
        path_coords[0]  = [origin_x, origin_y]
        path_coords[-1] = list(tes_geom_map[best_node])

    t_min  = best_d / cfg.walking_speed_m_per_min
    line   = LineString([(c[0], c[1]) for c in path_coords]) if len(path_coords) >= 2 else None

    return {
        "found":            True,
        "travel_time_min":  round(t_min, 2),
        "distance_m":       round(best_d, 1),
        "tes_kategori":     tes_kat_map.get(best_node, "unknown"),
        "tes_name":         tes_name_map.get(best_node, "Fasilitas TES"),
        "tes_coords":       list(tes_geom_map[best_node]),
        "path_coords":      path_coords,
        "geojson_linestring": line.__geo_interface__ if line else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 18. FULL PIPELINE (dipanggil oleh endpoint /api/baseline & /api/simulate)
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline(
    gdf_base: gpd.GeoDataFrame,
    roads_raw: Optional[gpd.GeoDataFrame],
    tes_raw: Dict[str, gpd.GeoDataFrame],
    skenario: str,
    intensity: float,
    cfg: Cfg,
    k_opt_override: Optional[int] = None,
    t_pen_override: Optional[float] = None,
    cut_roads: Optional[List[dict]] = None,
    G_override: Optional[nx.Graph] = None,
    nl_override=None,
    tn_override=None,
    w_override=None,
    baseline_times_override: Optional[np.ndarray] = None,
    psi_array_override: Optional[np.ndarray] = None,
    bypass_cache: bool = False,
    skip_evaluation: bool = False,
    fast_clustering: bool = False,
) -> Tuple[gpd.GeoDataFrame, dict, pd.DataFrame, dict]:
    """
    Pipeline lengkap: simulate → filter_tes → build_network → distances →
    preprocess → determine_k → clustering → evaluate → detect_semu.
    """

    sk = cfg.sk_key(skenario, intensity)
    logger.info(f"[run_pipeline] START | skenario={skenario} intensity={intensity} sk={sk}")

    # ── 0. Cek Cache (Hanya jika tidak ada blokade jalan dan tidak bypass) ─────
    pct = int(intensity * 100)
    sk_tag = f"{pct}pct"
    col_cl = f"cl_sdwfcm_{skenario}_{pct}pct"
    col_mem = f"mem_sdwfcm_{skenario}_{pct}pct"
    col_tm = f"waktu_min_{skenario}_{pct}pct"
    col_iso = f"iso_{skenario}_{pct}pct"
    
    can_use_cache = (
        not bypass_cache and
        not cut_roads and 
        col_cl in gdf_base.columns and 
        col_mem in gdf_base.columns and 
        col_tm in gdf_base.columns
    )
    
    if can_use_cache:
        logger.info(f"[run_pipeline] CACHE HIT: Mengambil hasil precomputed untuk {skenario} {pct}%")
        gdf_sim = gdf_base.copy()
        
        # Ambil hasil dari cache
        tm = gdf_sim[col_tm].values
        labs = gdf_sim[col_cl].values
        mem = gdf_sim[col_mem].values
        
        # Pasang ke kolom standar
        gdf_sim[f"waktu_tes_min_{skenario}"] = tm
        gdf_sim[f"waktu_tes_min_{sk}"]       = tm
        gdf_sim["cluster_sdwfcm"]           = labs
        gdf_sim["membership_max"]           = mem
        
        # Hitung aksesibilitas standar
        aks = np.where(tm <= cfg.golden_time_min, 1,
                       np.where(tm <= cfg.isolation_time_threshold, 2, 3))
        gdf_sim[f"aksesibilitas_{sk}"]       = aks
        gdf_sim[f"aksesibilitas_{skenario}"] = aks

        finite_tm = tm[np.isfinite(tm) & (tm > 0)]
        # Offline cache stores only the minimum travel time, not the original
        # per-category t_pen metadata. Isolated grids are encoded at the
        # scenario/intensity penalty, so infer that penalty from the cached
        # travel-time column instead of using a stale baseline override.
        t_pen_cache = float(np.max(finite_tm)) if finite_tm.size else 200.0
        if col_iso in gdf_base.columns:
            is_isolated_cache = gdf_base[col_iso].fillna(0).astype(bool).values
        else:
            is_isolated_cache = np.isclose(tm, t_pen_cache, rtol=0.0, atol=1e-6)

        # Deteksi Titik Aman Semu
        gdf_sim["titik_aman_semu"] = 0
        semu_gdf = detect_titik_aman_semu(
            gdf_sim, labs, skenario, sk, cfg,
            baseline_times=baseline_times_override,
            psi_array=psi_array_override,
            t_pen=t_pen_cache,
            is_isolated_override=is_isolated_cache,
        )
        if len(semu_gdf) > 0:
            gdf_sim.loc[semu_gdf.index, "titik_aman_semu"] = 1

        return gdf_sim, {}, pd.DataFrame(), {"k": int(len(np.unique(labs))), "t_pen": float(t_pen_cache)}

    # ── 1. Simulasi Bencana (Hazard Map) ──────────────────────────────────────
    gdf_sim, roads_sim, tes_sim, mask_dampak = simulate_hazard(
        gdf_base,
        roads_raw,
        tes_raw, skenario, intensity, cfg,
    )
    gdf_sim = gdf_sim.reset_index(drop=True)

    # ── 2. Filter TES ─────────────────────────────────────────────────────────
    tes_v, _ = filter_tes(tes_sim, skenario, cfg)

    # ── 3. Build / gunakan Network ────────────────────────────────────────────
    G = nl = tn = None

    if G_override is not None:
        # Digunakan oleh /api/simulate ketika ada cut_roads
        G, nl, tn = G_override, nl_override, tn_override
    elif roads_sim is not None:
        G, nl, tn = build_road_graph(roads_sim, skenario, intensity, cfg)

    # ── 4. Hitung jarak ───────────────────────────────────────────────────────
    if G is not None and len(G.nodes()) > 0:
        tpk, tm, _, iso, opsi = compute_distances(
            gdf_sim, skenario, tes_v, cfg, intensity,
            None, None, None, G, nl, tn,
        )
    else:
        tpk  = {k: np.full(len(gdf_sim), cfg.unreachable_time) for k in cfg.kategori_fac}
        tm   = np.full(len(gdf_sim), cfg.unreachable_time)
        iso  = {k: np.ones(len(gdf_sim), int)  for k in cfg.kategori_fac}
        opsi = np.zeros(len(gdf_sim), int)

    # T_max / T_penalty
    if t_pen_override is not None:
        t_pen = t_pen_override
        logger.info(f"[run_pipeline] Menggunakan t_pen baseline: {t_pen:.2f} mnt")
    else:
        t_max  = calc_t_max(tpk, cfg)
        t_pen  = 3.0 * t_max
        logger.info(f"[run_pipeline] Dihitung t_pen baru: {t_pen:.2f} mnt")

    # Ganti jarak yang tak terjangkau (inf/9999) dengan t_pen
    for k2 in cfg.kategori_fac:
        mask_unreachable = (tpk[k2] >= cfg.unreachable_time * 0.9) | np.isinf(tpk[k2])
        tpk[k2] = np.where(mask_unreachable, t_pen, tpk[k2])

    # Re-compute iso dan opsi dengan t_pen yang sudah dikunci
    iso    = {k: (tpk[k] >= t_pen).astype(int) for k in cfg.kategori_fac}
    opsi   = np.column_stack([(tpk[k] < t_pen).astype(int) for k in cfg.kategori_fac]).sum(axis=1)
    tm     = np.column_stack(list(tpk.values())).min(axis=1)

    # Simpan ke GeoDataFrame
    for k2, arr in tpk.items():
        gdf_sim[f"waktu_tes_{k2}_{sk}"]       = arr
        gdf_sim[f"waktu_tes_{k2}_{skenario}"] = arr
    gdf_sim[f"waktu_tes_min_{sk}"]       = tm
    gdf_sim[f"waktu_tes_min_{skenario}"] = tm
    aks = np.where(tm <= cfg.golden_time_min, 1,
                   np.where(tm <= cfg.isolation_time_threshold, 2, 3))
    gdf_sim[f"aksesibilitas_{sk}"]       = aks
    gdf_sim[f"aksesibilitas_{skenario}"] = aks
    for k2 in cfg.kategori_fac:
        gdf_sim[f"is_isolated_{k2}_{sk}"] = iso[k2]
    gdf_sim[f"jumlah_opsi_rute_{sk}"] = opsi

    # ── 5. Preprocessing / PCA ───────────────────────────────────────────────
    X_pca = preprocess(gdf_sim, skenario, sk, cfg, mask_dampak)

    # ── 6. K Optimal ──────────────────────────────────────────────────────────
    if k_opt_override is not None:
        k_opt = k_opt_override
        logger.info(f"[run_pipeline] Menggunakan K optimal dari baseline: {k_opt}")
    else:
        k_opt = determine_k(X_pca, skenario, cfg)
        logger.info(f"[run_pipeline] K optimal baru dihitung: {k_opt}")

    # ── 7. Build spatial weights (Reuse baseline if possible) ─────────────────
    if w_override is not None:
        w = w_override
    else:
        w = build_weights(gdf_sim)

    # ── 8. Clustering ─────────────────────────────────────────────────────────
    cl_results = run_all_clustering(
        gdf_sim, w, X_pca, k_opt, skenario, cfg, mask_dampak, fast_mode=fast_clustering
    )

    # ── 9. Pasang label SDWFCM ke GeoDataFrame ────────────────────────────────
    sdwfcm_res = cl_results.get("SDWFCM")
    if sdwfcm_res is not None:
        labs = sdwfcm_res.get("labels")
        if labs is not None:
            gdf_sim["cluster_sdwfcm"]      = labs
            gdf_sim["membership_max"]      = sdwfcm_res.get("max_membership")
            gdf_sim["cluster_sfcm"]        = (cl_results.get("SFCM") or {}).get("labels")
            gdf_sim["cluster_redcap"]      = (cl_results.get("REDCAP") or {}).get("labels")
            gdf_sim["cluster_skater"]      = (cl_results.get("SKATER") or {}).get("labels")
            # Deteksi titik aman semu (Hybrid Logic)
            gdf_sim["titik_aman_semu"]     = 0
            semu_gdf = detect_titik_aman_semu(
                gdf_sim, labs, skenario, sk, cfg, 
                baseline_times=baseline_times_override,
                psi_array=psi_array_override,
                t_pen=t_pen
            )
            if len(semu_gdf) > 0:
                gdf_sim.loc[semu_gdf.index, "titik_aman_semu"] = 1

    # ── 10. Evaluasi ───────────────────────────────────────────────────────────
    if skip_evaluation:
        eval_df = pd.DataFrame()
    else:
        try:
            eval_df = evaluate_all(cl_results, X_pca, gdf_sim, w, k_opt, skenario, cfg)
        except Exception as e:
            logger.error(f"[run_pipeline] Evaluasi gagal: {e}")
            eval_df = pd.DataFrame()

    logger.info(f"[run_pipeline] SELESAI | sk={sk}")
    return gdf_sim, cl_results, eval_df, {"k": k_opt, "t_pen": t_pen}

"""Modul komputasi dasar: pemuatan data, graf jaringan jalan, waktu tempuh ke TES,
simulasi dampak banjir, dan algoritma klasterisasi (SDWFCM, SFCM, REDCAP, SKATER).

Modul ini murni komputasi (tidak bergantung pada FastAPI). Alur analisis penelitian
disusun di backend/thesis.py; persamaan lengkap di docs/METODOLOGI.md.
"""

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
    """Konfigurasi terpusat: lokasi data dan seluruh parameter model."""
    # ── Path data (di-override dari main.py via environment / argumen) ────────
    base_dir: str = "./data"
    target_crs: str = "EPSG:32749"

    # ── Kolom hazard ──────────────────────────────────────────────────────────
    hazard_col_map: Dict[str, str] = field(default_factory=lambda: {
        "banjir":          "banjir",
        "banjir_bandang":  "banjir_bandang",
        "tanah_longsor":   "tanah_longsor",
    })
    # Skripsi: hanya bencana banjir, 4 level (Baseline, Rendah, Sedang, Tinggi)
    skenario_list: List[str] = field(default_factory=lambda: ["banjir"])
    intensity_levels: List[float] = field(default_factory=lambda: [
        0.0, 0.25, 0.50, 0.75,
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
    # Bobot tetangga terdampak banjir pada suku spasial d_s. 1,0 = nonaktif: pada desain data
    # gabungan grid terdampak (Tergenang) dikeluarkan dari klasterisasi, sehingga tidak ada
    # tetangga terdampak yang perlu dibobot khusus. Parameter dipertahankan untuk dokumentasi.
    sdwfcm_impact_weight: float = 1.0

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
    threshold_n_classes: int = 3

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


ORIGINAL_ID_COL = "Id"   # ID grid asli di Kulonprogo_Ready4.gpkg


def original_grid_ids(gdf: gpd.GeoDataFrame) -> pd.Series:
    """ID grid asli dari GPKG (kolom `Id`) bila unik dan lengkap; bila tidak, ID
    deterministik dari koordinat centroid "E{cx:.0f}_N{cy:.0f}" (EPSG:32749)."""
    col = gdf.get(ORIGINAL_ID_COL)
    if col is not None and col.notna().all() and col.is_unique:
        return col.astype("int64").astype(str).values
    logger.warning(f"[load_data] Kolom '{ORIGINAL_ID_COL}' tidak unik/lengkap -> ID dari centroid")
    c = gdf.geometry.centroid
    ids = pd.Series([f"E{x:.0f}_N{y:.0f}" for x, y in zip(c.x, c.y)])
    if not ids.is_unique:
        raise ValueError("ID centroid tidak unik")
    return ids.values


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
    gdf["id_grid_asli"] = original_grid_ids(gdf)

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
# 4. MATRIKS BOBOT SPASIAL (ROOK)
# ══════════════════════════════════════════════════════════════════════════════
def build_weights(gdf: gpd.GeoDataFrame):
    """Matriks bobot spasial ketetanggaan rook (fallback queen), distandardisasi baris.

    Grid tanpa tetangga (island) diberi 2 tetangga terdekat (KNN). Komponen yang
    tidak terhubung disambungkan ke komponen lain melalui pasangan grid terdekat,
    sehingga graf ketetanggaan terhubung. Dipakai oleh SFCM, REDCAP, SKATER, dan Moran's I.
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
# 6. GRAF JARINGAN JALAN
# ══════════════════════════════════════════════════════════════════════════════
def road_closed_mask(roads: gpd.GeoDataFrame, skenario: str, intensity: float, cfg: Cfg) -> np.ndarray:
    """Ruas ditutup ⇔ norm_haz(kelas bahaya ruas) × intensitas ≥ impact_closure_threshold."""
    hc = cfg.hazard_col_map.get(skenario, skenario)
    if hc not in roads.columns:
        return np.zeros(len(roads), dtype=bool)
    haz = roads[hc].fillna(0).astype(int).map(cfg.norm_haz).to_numpy(dtype=float)
    return haz * intensity >= cfg.impact_closure_threshold


def build_road_graph(roads: gpd.GeoDataFrame, skenario: str, intensity: float, cfg: Cfg):
    """Graf tak berarah dari segmen jalan yang tidak ditutup banjir.

    Ruas ditutup bila norm_haz(kelas bahaya ruas) × intensitas ≥ impact_closure_threshold.
    Simpul = koordinat ujung segmen (dibulatkan 0,01 m); bobot sisi = panjang segmen (m),
    diambil yang terpendek bila ada segmen ganda.
    Returns: (G, node_array, kdtree)
    """
    n_rm = n_ok = 0
    edge_weights: Dict[Tuple[tuple, tuple], float] = {}

    closed = road_closed_mask(roads, skenario, intensity, cfg)
    geoms = roads.geometry.to_numpy()

    for idx, geom in enumerate(geoms):
        if geom is None or geom.is_empty:
            continue
        if closed[idx]:
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
# ══════════════════════════════════════════════════════════════════════════════
def filter_tes(tes_raw: Dict[str, gpd.GeoDataFrame], skenario: str, cfg: Cfg):
    """TES valid = titik dengan kelas bahaya < tes_hazard_threshold.

    Kelas bahaya TES yang terkena grid terdampak (lihat simulate_hazard) sudah
    dinaikkan sebelum fungsi ini dipanggil.
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
# 8. WAKTU TEMPUH KE TES (DIJKSTRA MULTI-SUMBER)
# ══════════════════════════════════════════════════════════════════════════════
SNAP_MAX_M = 300.0    # batas snapping centroid grid / titik TES ke simpul jalan
_EPS_M = 1e-6         # bobot minimum sisi sumber virtual (csgraph mengabaikan bobot 0)


def graph_csr(G: nx.Graph, nl: np.ndarray) -> csr_matrix:
    """Matriks ketetanggaan berbobot (panjang sisi, m) dengan urutan simpul = nl."""
    return nx.to_scipy_sparse_array(G, nodelist=[tuple(x) for x in nl], weight="weight", format="csr")


def snap_points(xy: np.ndarray, tn, max_snap: float = SNAP_MAX_M):
    """Simpul jalan terdekat per titik. Returns (jarak_m, indeks_simpul, ok)."""
    d, idx = tn.query(np.asarray(xy, float), k=1)
    return d, idx, d <= max_snap


def network_distance_from_sources(csr: csr_matrix, src_nodes: np.ndarray,
                                  src_offset_m: np.ndarray) -> np.ndarray:
    """Jarak terpendek (m) setiap simpul ke sumber terdekat, dengan jarak awal per sumber
    (= ruas snapping sumber). Sumber virtual tambahan dihubungkan ke semua simpul sumber
    dengan bobot offset (+1e-6 m), lalu satu Dijkstra dijalankan dari simpul virtual."""
    n = csr.shape[0]
    if len(src_nodes) == 0:
        return np.full(n, np.inf)
    best = {}
    for nd, off in zip(np.asarray(src_nodes, int), np.asarray(src_offset_m, float)):
        if nd not in best or off < best[nd]:
            best[nd] = off
    nodes = np.fromiter(best.keys(), int)
    offs = np.fromiter(best.values(), float) + _EPS_M
    extra = csr_matrix((offs, (np.full(len(nodes), n), nodes)), shape=(n + 1, n + 1))
    aug = sp.bmat([[csr, None], [None, csr_matrix((1, 1))]], format="csr") + extra
    from scipy.sparse.csgraph import dijkstra as _dijkstra
    d = _dijkstra(aug, directed=False, indices=n)[:n]
    return d - _EPS_M


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
    """Waktu tempuh (menit) dari centroid setiap grid ke TES terdekat per kategori.

    Jarak = (centroid grid → simpul jalan terdekat) + (jarak jaringan antarsimpul)
          + (simpul jalan terdekat TES → titik TES), dibagi walking_speed_m_per_min.
    Snapping centroid dan TES maksimum SNAP_MAX_M (300 m). Untuk tiap kategori dicari TES
    dengan total jarak terkecil (Dijkstra dari sumber virtual yang terhubung ke simpul TES
    berbobot ruas snapping TES). Grid/TES yang gagal di-snap atau tidak terhubung diberi
    waktu penalti `t_pen`.
    Returns: (tpk, t_min, grid_node_idx, iso_per_kategori, jumlah_opsi)
    """
    n = len(gdf)
    cx = gdf["cx"].values if "cx" in gdf.columns else gdf.geometry.centroid.x.values
    cy = gdf["cy"].values if "cy" in gdf.columns else gdf.geometry.centroid.y.values
    tp = t_pen if (t_pen and t_pen > 0) else cfg.unreachable_time
    speed = cfg.walking_speed_m_per_min
    logger.info(f"[compute_distances] Dijkstra sumber virtual [{skenario}|{intensity:.2f}]")

    if tes_v is None or len(tes_v) == 0 or tn is None or len(nl) == 0:
        tpk = {k: np.full(n, tp) for k in cfg.kategori_fac}
        return tpk, np.full(n, tp), [None] * n, {k: np.ones(n, int) for k in cfg.kategori_fac}, np.zeros(n, int)

    csr = graph_csr(G, nl)
    g_d, g_idx, g_ok = snap_points(np.column_stack((cx, cy)), tn)

    tpk = {}
    for kat in cfg.kategori_fac:
        sub = tes_v[tes_v["kategori"] == kat]
        arr = np.full(n, np.inf)
        if len(sub):
            t_xy = np.column_stack([sub.geometry.x.values, sub.geometry.y.values])
            t_d, t_idx, t_ok = snap_points(t_xy, tn)
            if t_ok.any():
                d_node = network_distance_from_sources(csr, t_idx[t_ok], t_d[t_ok])
                arr[g_ok] = g_d[g_ok] + d_node[g_idx[g_ok]]
        t = arr / speed
        tpk[kat] = np.where(np.isfinite(t), t, tp)

    tm = np.column_stack(list(tpk.values())).min(axis=1)
    iso = {k: (tpk[k] >= tp).astype(int) for k in cfg.kategori_fac}
    opsi = np.column_stack([(tpk[k] < tp).astype(int) for k in cfg.kategori_fac]).sum(axis=1)
    return tpk, tm, np.where(g_ok, g_idx, -1).tolist(), iso, opsi


def calc_t_max(tpk: dict, cfg: Cfg) -> float:
    """T_max = waktu tempuh MAKSIMUM yang valid (terjangkau, > 0) di seluruh kategori TES.

    Pada Baseline, waktu penalti untuk grid tak terjangkau ditetapkan
    T_pen = 3 × T_max dan dipakai tetap untuk semua level.
    """
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
# 9. SIMULASI DAMPAK BANJIR
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
    """Simulasi dampak banjir pada grid dan TES untuk satu intensitas.

    p = (h − h_min) / (h_max − h_min) dari kelas bahaya grid h (0–3).
    Grid terdampak ⇔ intensitas > 0 ∧ p ≥ 1 − intensitas ∧ p > 0.
    TES dalam radius 50 m dari grid terdampak dan berkelas bahaya < tes_hazard_threshold
    dinaikkan kelasnya ke road_break_threshold (sehingga tidak valid di filter_tes).
    Penutupan ruas jalan dihitung terpisah di build_road_graph.
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
# 12. FUNGSI BANTU REDCAP (dipercepat numba bila tersedia)
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
# 13. ALGORITMA KLASTERISASI
# ══════════════════════════════════════════════════════════════════════════════

def fuzzy_membership_update(dt: np.ndarray, m: float) -> np.ndarray:
    """Aturan update keanggotaan FCM untuk jarak KUADRAT dt:
        u_ik = 1 / Σ_l (dt_ik / dt_il)^(1/(m−1))
    (setara dengan bentuk baku 1 / Σ_l (‖x_i−v_k‖ / ‖x_i−v_l‖)^(2/(m−1)) untuk jarak tak-kuadrat).
    """
    r = dt[:, :, None] / dt[:, None, :]
    U = 1.0 / (r ** (1.0 / (m - 1.0))).sum(axis=2)
    U = np.clip(U, 1e-10, None)
    return U / U.sum(axis=1, keepdims=True)


def sdwfcm_distances(X: np.ndarray, U: np.ndarray, W: csr_matrix, dw: np.ndarray,
                     m: float, alpha: float):
    """Jarak SDWFCM untuk keanggotaan U (dipakai bersama oleh fit() dan fungsi objektif).

        v_k   = Σ_i u_ik^m x_i / Σ_i u_ik^m
        d_a   = ‖x_i − v_k‖² (+1e-10)
        d_s   = Σ_j W_ij ω_j d_a,jk u_jk^m / Σ_j W_ij u_jk^m     (ω_j = bobot dampak tetangga j)
        d_t   = (1 − α) d_a + α d_s
    Returns: (centers, d_a, d_s, d_t)
    """
    k = U.shape[1]
    Um = U ** m
    centers = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
    da = cdist(X, centers) ** 2 + 1e-10
    We = W @ sp.diags(dw, format="csr")
    ds = np.zeros_like(da)
    for ci in range(k):
        ds[:, ci] = (We @ (da[:, ci] * Um[:, ci])) / ((W @ Um[:, ci]) + 1e-10)
    dt = np.clip((1 - alpha) * da + alpha * ds, 1e-10, None)
    return centers, da, ds, dt


def sdwfcm_objective_value(X: np.ndarray, U: np.ndarray, W: csr_matrix, dw: np.ndarray,
                           m: float, alpha: float) -> float:
    """Fungsi objektif SDWFCM J(U) = Σ_i Σ_k u_ik^m · d_t,ik(U), dengan d_t dari sdwfcm_distances."""
    _, _, _, dt = sdwfcm_distances(X, U, W, dw, m, alpha)
    return float(((U ** m) * dt).sum())


def impact_weights(n: int, mask_dampak, impact_weight: float) -> np.ndarray:
    """ω_j = impact_weight untuk grid terdampak banjir, 1 untuk lainnya."""
    dw = np.ones(n)
    if mask_dampak is not None and np.any(mask_dampak):
        dw[np.asarray(mask_dampak, bool)] = impact_weight
    return dw


class SpatialDistanceWeightedFCM:
    """Spatial Distance-Weighted Fuzzy C-Means (SDWFCM).

    Jarak gabungan d_t = (1 − α)·d_a + α·d_s, dengan d_a jarak Euclidean kuadrat
    ke pusat klaster dan d_s rata-rata tertimbang d_a·u^m tetangga (bobot KNN-Gaussian
    W, dan bobot tambahan untuk tetangga terdampak banjir). Persamaan lengkap:
    docs/METODOLOGI.md.
    """
    def __init__(self, k=5, m=1.7, alpha=0.5, sigma=None, knn=8,
                 max_iter=150, tol=1e-4, rs=42, impact_weight=2.0, track_objective=False):
        self.k = k; self.m = m; self.alpha = alpha; self.sigma = sigma
        self.knn = knn; self.max_iter = max_iter; self.tol = tol; self.rs = rs
        self.impact_weight = impact_weight; self.track_objective = track_objective
        self.labels_ = self.U_ = self.max_membership_ = self.centers_ = None
        self.objective_ = None; self.objective_history_ = []; self.n_iter_ = 0

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

    def fit(self, X, gdf_or_coords=None, mask_dampak=None, W: Optional[csr_matrix] = None):
        """Iterasi: d_t(U) → U_baru = fuzzy_membership_update(d_t, m), sampai ‖U_baru − U‖_F < tol.

        Inisialisasi: np.random.seed(rs); U ~ Dirichlet(1,…,1).
        W: matriks bobot spasial yang sudah dihitung (mis. blok-diagonal per level pada data
        gabungan); bila None, W KNN-Gaussian dibangun dari koordinat `gdf_or_coords`.
        objective_ = J(U_akhir); objective_history_ berisi J(U_t) per iterasi bila
        track_objective=True.
        """
        np.random.seed(self.rs)
        n, _ = X.shape; k = self.k; m = self.m
        if W is None:
            W = self._build_W(gdf_or_coords)
        else:
            self._sigma = self.sigma
        self.W_ = W
        dw = impact_weights(n, mask_dampak, self.impact_weight)
        U = np.random.dirichlet(np.ones(k), size=n)
        self.objective_history_ = []
        if self.track_objective:
            self.objective_history_.append(sdwfcm_objective_value(X, U, W, dw, m, self.alpha))
        it = 0
        for it in range(self.max_iter):
            centers, _, _, dt = sdwfcm_distances(X, U, W, dw, m, self.alpha)
            Un   = fuzzy_membership_update(dt, m)
            diff = np.linalg.norm(Un - U)
            U    = Un
            if self.track_objective:
                self.objective_history_.append(sdwfcm_objective_value(X, U, W, dw, m, self.alpha))
            if diff < self.tol:
                logger.info(f"[SDWFCM] konvergen pada iterasi {it} | diff={diff:.6f}")
                break
        self.n_iter_          = it + 1
        self.U_               = U
        self.labels_          = np.argmax(U, axis=1)
        self.max_membership_  = U.max(axis=1)
        self.centers_         = centers
        self.objective_       = sdwfcm_objective_value(X, U, W, dw, m, self.alpha)
        sig = f"{self._sigma:.2f}" if self._sigma else "W eksternal"
        logger.info(f"[SDWFCM] {len(set(self.labels_))} klaster | σ={sig} | J={self.objective_:.4f}")
        return self


def neighbor_mean_operator(w, n: int) -> Tuple[csr_matrix, np.ndarray]:
    """Operator rata-rata tetangga R (R_ij = 1/|N_i| untuk j ∈ N_i) dari libpysal W, dan
    penanda grid yang punya tetangga."""
    rows, cols = [], []
    for i in range(n):
        for j in w.neighbors.get(i, []):
            rows.append(i); cols.append(int(j))
    B = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    deg = np.asarray(B.sum(axis=1)).ravel()
    has = deg > 0
    R = sp.diags(np.where(has, 1.0 / np.maximum(deg, 1), 0.0)) @ B
    return R.tocsr(), has


def sfcm_distances(X, U, R, has_nb, m: float, alpha: float):
    """Jarak SFCM: d_s,ik = (rata-rata d_a,jk tetangga) × (rata-rata u_jk tetangga);
    grid tanpa tetangga memakai d_s = d_a. d_t = (1 − α) d_a + α d_s."""
    Um = U ** m
    centers = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
    da = cdist(X, centers) ** 2 + 1e-10
    ds = (R @ da) * (R @ U)
    ds[~has_nb] = da[~has_nb]
    dt = np.clip((1 - alpha) * da + alpha * ds, 1e-10, None)
    return centers, dt


class SpatialFuzzyCMeans:
    """Spatial Fuzzy C-Means (SFCM), algoritma pembanding.

    Jarak FCM standar dimodifikasi dengan suku spasial dari tetangga rook:
    d_t = (1 − α)·d_a + α·d_s, d_s,ik = rata-rata d_a tetangga × rata-rata u_k tetangga.
    Fungsi objektif (untuk memilih inisialisasi terbaik): J = Σ_i Σ_k u_ik^m · d_t,ik.
    """
    def __init__(self, k=5, m=2.0, alpha=0.5, max_iter=150, tol=1e-4, rs=42):
        self.k = k; self.m = m; self.alpha = alpha
        self.max_iter = max_iter; self.tol = tol; self.rs = rs
        self.labels_ = self.U_ = self.max_membership_ = None
        self.objective_ = None

    def fit(self, X, w, operator: Optional[Tuple[csr_matrix, np.ndarray]] = None):
        np.random.seed(self.rs)
        n, _ = X.shape; k = self.k; m = self.m
        R, has_nb = operator if operator is not None else neighbor_mean_operator(w, n)
        U   = np.random.dirichlet(np.ones(k), size=n)
        for it in range(self.max_iter):
            _, dt = sfcm_distances(X, U, R, has_nb, m, self.alpha)
            Un  = fuzzy_membership_update(dt, m)
            diff = np.linalg.norm(Un - U)
            U    = Un
            if diff < self.tol:
                logger.info(f"[SFCM] konvergen pada iterasi {it} | diff={diff:.6f}")
                break
        _, dt = sfcm_distances(X, U, R, has_nb, m, self.alpha)
        self.objective_      = float(((U ** m) * dt).sum())
        self.U_              = U
        self.labels_         = np.argmax(U, axis=1)
        self.max_membership_ = U.max(axis=1)
        logger.info(f"[SFCM] {len(set(self.labels_))} klaster | J={self.objective_:.4f}")
        return self


class REDCAPManual:
    """REDCAP (regionalisasi hierarkis berkendala kontiguitas), algoritma pembanding.

    Region bertetangga digabung berurutan menurut ketidakmiripan (linkage) yang
    dikalikan penalti ukuran (n^size_alpha) dan penalti isolasi, sampai tersisa K region.
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


def run_skater(adjacency: csr_matrix, X_pca: np.ndarray, k: int, cfg: Cfg) -> np.ndarray:
    """SKATER (Assunção dkk., 2006) via spopt.region.Skater, algoritma pembanding.

    adjacency: ketetanggaan biner simetris (rook). Ukuran minimum region = `floor`
    (cfg.skater_min_region). Tidak ada fallback: bila spopt gagal, galat diteruskan ke
    pemanggil agar dilaporkan apa adanya.
    """
    if not SKATER_OK:
        raise ImportError("spopt tidak terpasang")
    from libpysal.weights import W as _W
    w = _W.from_sparse(csr_matrix(adjacency, dtype=float))
    cols = [f"pc{i + 1}" for i in range(X_pca.shape[1])]
    frame = gpd.GeoDataFrame(pd.DataFrame(X_pca, columns=cols))
    model = Skater(frame, w, cols, n_clusters=k, floor=cfg.skater_min_region)
    model.solve()
    labs = np.asarray(model.labels_, dtype=int)
    logger.info(f"[SKATER] spopt: {len(np.unique(labs))} klaster")
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
        from .thesis import rook_adjacency
        return run_skater(rook_adjacency(w), X_pca, k, cfg)

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



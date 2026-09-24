"""Pipeline analisis penelitian: aksesibilitas spasial TES banjir Kulon Progo.

Ringkasan alur (rincian dan persamaan: docs/METODOLOGI.md):
  1. Empat level banjir berdasarkan kelas bahaya yang ditutup (Baseline, Rendah, Sedang,
     Tinggi) pada grid 100 × 100 m; grid terdampak berstatus "Tergenang". Waktu tempuh
     centroid → titik TES per kategori (ruas snapping + jaringan jalan, 80 m/menit).
  2. Data gabungan: semua pasangan (grid, level) non-Tergenang; praproses di-fit sekali
     pada data gabungan.
  3. SDWFCM dengan W KNN-Gaussian blok-diagonal per level; K dipilih dengan stabilitas
     subsampel; klaster dinomori menurut rata-rata waktu tempuh minimum.
  4. Analisis transisi antarlevel (state tipologi + Tergenang), perbandingan algoritma
     di Baseline, dan deteksi Titik Aman Semu (TAS, Non-TAS, TES terdekat tidak terjangkau, Tergenang).
"""
import logging
import time
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
from scipy.sparse import csr_matrix
from scipy.optimize import linear_sum_assignment
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import PowerTransformer, RobustScaler
from esda.moran import Moran

from .engine import (
    EVAC_TIME_MIN,
    EVAC_TIME_SENS,
    Cfg,
    REDCAPManual,
    SpatialDistanceWeightedFCM,
    SpatialFuzzyCMeans,
    build_road_graph,
    calc_t_max,
    road_closed_mask,
    impact_weights,
    sdwfcm_objective_value,
    compute_distances,
    filter_tes,
    fuzzy_membership_update,
    neighbor_mean_operator,
    graph_csr,
    run_skater,
    simulate_hazard,
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 1. KONSTANTA PENELITIAN
# ══════════════════════════════════════════════════════════════════════════════
SKENARIO = "banjir"

# Level didefinisikan oleh kelas bahaya banjir InaRisk yang ditutup (grid berkelas tersebut
# tergenang dan ruas jalan berkelas tersebut ditutup):
#   Baseline = tidak ada, Rendah = kelas 3, Sedang = kelas ≥ 2, Tinggi = kelas ≥ 1.
# `intensity` hanya detail implementasi: simulate_hazard dan build_road_graph menerima angka
# intensitas yang menghasilkan himpunan kelas yang sama persis (dibuktikan di
# tests/test_level_kelas.py) dan dipakai sebagai kunci cache graf jalan di dashboard.
LEVELS: List[dict] = [
    {"key": "baseline", "label": "Baseline", "kelas_ditutup": [],
     "label_lengkap": "Baseline (tidak ada kelas ditutup)", "intensity": 0.00},
    {"key": "rendah", "label": "Rendah", "kelas_ditutup": [3],
     "label_lengkap": "Level Rendah (kelas 3 ditutup)", "intensity": 0.25},
    {"key": "sedang", "label": "Sedang", "kelas_ditutup": [2, 3],
     "label_lengkap": "Level Sedang (kelas ≥ 2 ditutup)", "intensity": 0.50},
    {"key": "tinggi", "label": "Tinggi", "kelas_ditutup": [1, 2, 3],
     "label_lengkap": "Level Tinggi (kelas ≥ 1 ditutup)", "intensity": 0.75},
]
LEVEL_KEYS = [lv["key"] for lv in LEVELS]
LEVEL_BY_KEY = {lv["key"]: lv for lv in LEVELS}

K_RANGE = range(2, 11)     # kandidat jumlah klaster
PCA_VARIANCE = 0.80       # proporsi varians kumulatif yang dipertahankan PCA
IQR_FACTOR = 3.0          # pagar pencilan ekstrem Tukey: [Q1 − 3·IQR, Q3 + 3·IQR]
VARIANCE_MIN = 1e-3
IINDEX_P = 2
SDWFCM_N_INIT = 10        # jumlah inisialisasi acak SDWFCM (semua algoritma fuzzy)
SDWFCM_SEED = 42          # seed awal; inisialisasi ke-i memakai SDWFCM_SEED + i
STABILITY_SEEDS = [SDWFCM_SEED + i for i in range(SDWFCM_N_INIT)]   # 42–51
SUBSAMPLE_B = 10          # jumlah subsampel stabilitas K (diturunkan ke 5 hanya bila estimasi > 3 jam)
SUBSAMPLE_FRAC = 0.80     # proporsi id_grid unik per subsampel
SUBSAMPLE_N_INIT = 3      # inisialisasi per subsampel (seed 42–44), diambil J terkecil
SUBSAMPLE_SEED = 20240    # seed pemilihan subsampel ke-b = SUBSAMPLE_SEED + b
K_ARI_TOLERANCE = 0.01    # K dengan rerata ARI subsampel ≥ maksimum − 0,01 dianggap setara → K terkecil
DUNN_SAMPLE = 2000        # ukuran sampel grid untuk Dunn titik-ke-titik (O(n²))
DUNN_SEEDS = [42, 43, 44, 45, 46]
SILHOUETTE_SAMPLE = 10000
SILHOUETTE_SEED = 42
MORAN_PERMUTATIONS = 999
MORAN_PERMUTATION_SEED = 42   # esda.Moran tidak punya parameter seed → seed global di-set sebelum dipanggil
DEGENERATE_MAX_SHARE = 0.90   # partisi degeneratif: klaster terbesar > 90% grid
K_OUTPUT = (2, 3, 4)          # keluaran lengkap disusun untuk K ini (model utama diputuskan peneliti)
AKSES_STATUS = {0: "Terjangkau", 1: "Jauh", 2: "Terputus", 3: "Tergenang"}   # padanan Li dkk. (2026)
TAS_MIN_EUCLID_M = 50.0   # jarak minimum (setengah lebar grid 100 m) untuk T_ideal DAN T_aktual
TAS_DI_ABSOLUTE = 2.0     # aturan utama TAS: DI_t ≥ 2 …
TAS_T_IDEAL_MAX = 5.0     # … dan T_ideal ≤ 5 menit (garis lurus ≤ 400 m pada 80 m/menit) …
TAS_T_AKTUAL_MIN = EVAC_TIME_MIN   # … dan T_aktual ≥ batas waktu evakuasi (30 menit)
# Status TAS 2 = TES terdekat (Euclidean) tidak terjangkau lewat jaringan (T_aktual = penalti). Berbeda
# dengan kategori akses "Terputus" (AKSES_STATUS 2: tidak mencapai TES mana pun); lihat METODOLOGI §11.
TAS_STATUS = {0: "Non-TAS", 1: "TAS", 2: "TES terdekat tidak terjangkau", 3: "Tergenang"}
TERGENANG = "Tergenang"   # status grid yang terdampak (mask simulasi) pada suatu level

FEATURE_LABELS = {
    "Road_Density_mean":      "Kepadatan Jaringan Jalan",
    "banjir":                 "Indeks Bahaya Banjir",
    "waktu_tes_pendidikan":   "Waktu TES Pendidikan (menit)",
    "waktu_tes_kesehatan":    "Waktu TES Kesehatan (menit)",
    "waktu_tes_pemerintahan": "Waktu TES Pemerintahan (menit)",
    "waktu_tes_ibadah":       "Waktu TES Tempat Ibadah (menit)",
    "waktu_tes_gor":          "Waktu TES GOR/Gedung Serbaguna (menit)",
    "waktu_tes_min":          "Waktu TES Minimum (menit)",
    "jumlah_opsi_rute":       "Jumlah Opsi Rute",
    "is_isolated_pendidikan":   "Fasilitas Pendidikan Terisolasi",
    "is_isolated_kesehatan":    "Fasilitas Kesehatan Terisolasi",
    "is_isolated_pemerintahan": "Fasilitas Pemerintahan Terisolasi",
    "is_isolated_ibadah":       "Fasilitas Tempat Ibadah Terisolasi",
    "is_isolated_gor":          "Fasilitas GOR/Gedung Serbaguna Terisolasi",
    "is_isolated":              "Terisolasi dari Seluruh Kategori TES",
}


def level_from_intensity(intensity: float) -> dict:
    """Level terdekat untuk nilai intensitas numerik (kompatibilitas API lama)."""
    return min(LEVELS, key=lambda lv: abs(lv["intensity"] - float(intensity)))


def resolve_level(level: Optional[str] = None, intensity: Optional[float] = None) -> dict:
    if level and level in LEVEL_BY_KEY:
        return LEVEL_BY_KEY[level]
    return level_from_intensity(intensity or 0.0)


def feature_columns(cfg: Cfg) -> List[str]:
    """Variabel masukan klasterisasi (9 variabel aksesibilitas). Kelas bahaya banjir TIDAK
    menjadi fitur (tipologi murni menggambarkan aksesibilitas); kelas bahaya tetap dilaporkan
    sebagai variabel deskriptif pada profil klaster. Penanda isolasi per kategori TES dihitung
    untuk profil klaster; fitur klasterisasi memakai satu penanda is_isolated."""
    return (
        ["Road_Density_mean"]
        + [f"waktu_tes_{k}" for k in cfg.kategori_fac]
        + ["waktu_tes_min", "jumlah_opsi_rute", "is_isolated"]
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. AKSESIBILITAS PER LEVEL
# ══════════════════════════════════════════════════════════════════════════════
def compute_level_accessibility(
    gdf_base: gpd.GeoDataFrame,
    roads_raw: gpd.GeoDataFrame,
    tes_raw: Dict[str, gpd.GeoDataFrame],
    intensity: float,
    cfg: Cfg,
    t_pen: Optional[float] = None,
    graph_pack: Optional[tuple] = None,
) -> dict:
    """Simulasi banjir + network distance ke TES per kategori pada satu level.

    t_pen (penalti tidak terjangkau) dihitung pada Baseline (3 × T_max) dan
    dikunci untuk level lain agar nilai waktu tempuh dapat dibandingkan.
    """
    gdf_sim, roads_sim, tes_sim, mask = simulate_hazard(
        gdf_base, roads_raw, tes_raw, SKENARIO, intensity, cfg
    )
    gdf_sim = gdf_sim.reset_index(drop=True)
    tes_v, tes_stats = filter_tes(tes_sim, SKENARIO, cfg)

    if graph_pack is None:
        graph_pack = build_road_graph(roads_sim, SKENARIO, intensity, cfg)
    G, nl, tn = graph_pack

    tpk, _, _, _, _ = compute_distances(
        gdf_sim, SKENARIO, tes_v, cfg, intensity, None, None, None, G, nl, tn
    )
    if t_pen is None:
        t_pen = 3.0 * calc_t_max(tpk, cfg)

    out = pd.DataFrame({
        "id_grid": gdf_sim["id_grid"].values,
        "Road_Density_mean": gdf_sim["Road_Density_mean"].fillna(
            gdf_sim["Road_Density_mean"].median()).values,
        SKENARIO: gdf_sim[SKENARIO].fillna(0).values.astype(float),
        "tergenang": mask.astype(int),   # grid terdampak simulasi → status "Tergenang"
    })
    for kat in cfg.kategori_fac:
        arr = tpk[kat]
        unreachable = (arr >= cfg.unreachable_time * 0.9) | ~np.isfinite(arr)
        arr = np.where(unreachable, t_pen, np.minimum(arr, t_pen))
        out[f"waktu_tes_{kat}"] = arr
        out[f"is_isolated_{kat}"] = (arr >= t_pen).astype(int)
    tcols = [f"waktu_tes_{k}" for k in cfg.kategori_fac]
    out["waktu_tes_min"] = out[tcols].min(axis=1).values
    out["jumlah_opsi_rute"] = sum(
        (out[f"waktu_tes_{k}"] < t_pen).astype(int) for k in cfg.kategori_fac
    ).values
    out["is_isolated"] = (out["jumlah_opsi_rute"] == 0).astype(int)

    return {
        "df": out,
        "mask": mask,
        "tes_v": tes_v,
        "tes_stats": tes_stats,
        "t_pen": float(t_pen),
        "graph": (G, nl, tn),
        "n_roads_closed": int(_count_closed_roads(roads_raw, intensity, cfg)),
    }


def _count_closed_roads(roads: gpd.GeoDataFrame, intensity: float, cfg: Cfg) -> int:
    if roads is None:
        return 0
    return int(road_closed_mask(roads, SKENARIO, intensity, cfg).sum())


def grid_class_rule_mask(gdf_base, level: dict) -> np.ndarray:
    """Aturan kelas: grid tergenang ⇔ kelas bahaya banjir ∈ kelas_ditutup level."""
    return np.isin(gdf_base[SKENARIO].fillna(0).astype(int).values, level["kelas_ditutup"])


def road_class_rule_mask(roads, level: dict) -> np.ndarray:
    """Aturan kelas: ruas ditutup ⇔ kelas bahaya banjir ruas ∈ kelas_ditutup level."""
    return np.isin(roads[SKENARIO].fillna(0).astype(int).values, level["kelas_ditutup"])


# ══════════════════════════════════════════════════════════════════════════════
# 3. PRA-PEMROSESAN — DI-FIT SEKALI PADA DATA GABUNGAN
# ══════════════════════════════════════════════════════════════════════════════
CAPPED_COLUMNS = ["Road_Density_mean"]   # satu-satunya variabel yang di-capping (Tukey 3 × IQR)


class Preprocessor:
    """Pra-pemrosesan fitur yang di-fit SEKALI pada data gabungan (semua pasangan grid–level
    non-Tergenang).

    Tahapan (semua parameter diestimasi dari data fit):
      1. nilai pengisi median per kolom;
      2. capping Tukey [Q1 − 3·IQR, Q3 + 3·IQR] hanya untuk CAPPED_COLUMNS
         (waktu_tes_*, jumlah_opsi_rute, dan is_isolated tidak di-capping);
      3. seleksi fitur: pertahankan kolom dengan varians > VARIANCE_MIN (setelah capping);
      4. Yeo-Johnson (λ per kolom) + standardisasi (mean, simpangan baku populasi);
      5. RobustScaler (median, IQR);
      6. PCA dengan varians kumulatif ≥ PCA_VARIANCE.
    Parameter disimpan sebagai dict JSON (`to_dict`) agar transformasi identik dapat
    dipakai ulang (mis. oleh simulasi blokir jalan di dashboard).
    """

    def __init__(self, params: Optional[dict] = None):
        self.params = params

    @classmethod
    def fit(cls, df: pd.DataFrame, cfg: Cfg) -> "Preprocessor":
        cols = feature_columns(cfg)
        F = df[cols].astype(float)
        medians = {c: float(F[c].median()) for c in cols}
        F = F.fillna(medians)
        caps = {}
        for c in CAPPED_COLUMNS:
            q1, q3 = np.percentile(F[c].values, [25, 75])
            iqr = q3 - q1
            caps[c] = [float(q1 - IQR_FACTOR * iqr), float(q3 + IQR_FACTOR * iqr)]
            F[c] = np.clip(F[c].values, *caps[c])
        variances = {c: float(F[c].var()) for c in cols}
        kept = [c for c in cols if variances[c] > VARIANCE_MIN]

        pt = PowerTransformer(method="yeo-johnson", standardize=True).fit(F[kept].values)
        Y = pt.transform(F[kept].values)
        rs = RobustScaler().fit(Y)
        Z = rs.transform(Y)
        pca = PCA(n_components=PCA_VARIANCE, svd_solver="full").fit(Z)
        params = {
            "features_in": cols,
            "medians": medians,
            "caps": caps,
            "iqr_factor": IQR_FACTOR,
            "variance_min": VARIANCE_MIN,
            "variances_fit": variances,
            "n_baris_fit": int(len(F)),
            "features_kept": kept,
            "features_dropped": [c for c in cols if c not in kept],
            "yeojohnson_lambdas": [float(v) for v in pt.lambdas_],
            "yeojohnson_mean": [float(v) for v in pt._scaler.mean_],
            "yeojohnson_scale": [float(v) for v in pt._scaler.scale_],
            "robust_center": [float(v) for v in rs.center_],
            "robust_scale": [float(v) for v in rs.scale_],
            "pca_mean": [float(v) for v in pca.mean_],
            "pca_components": pca.components_.tolist(),
            "pca_explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
            "n_components": int(pca.n_components_),
            "explained_variance": float(pca.explained_variance_ratio_.sum()),
        }
        return cls(params)

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Terapkan parameter hasil fit (tanpa fit ulang)."""
        from scipy.stats import yeojohnson
        p = self.params
        F = df[p["features_in"]].astype(float).fillna(p["medians"])
        for c, (lo, hi) in p["caps"].items():
            F[c] = np.clip(F[c].values, lo, hi)
        cols = p["features_kept"]
        Y = np.column_stack([yeojohnson(F[c].values, lmbda=lam)
                             for c, lam in zip(cols, p["yeojohnson_lambdas"])])
        Y = (Y - np.asarray(p["yeojohnson_mean"])) / np.asarray(p["yeojohnson_scale"])
        Z = (Y - np.asarray(p["robust_center"])) / np.asarray(p["robust_scale"])
        return (Z - np.asarray(p["pca_mean"])) @ np.asarray(p["pca_components"]).T

    def info(self) -> dict:
        p = self.params
        return {k: p[k] for k in ("features_in", "features_kept", "features_dropped", "caps",
                                  "n_components", "explained_variance",
                                  "pca_explained_variance_ratio")}

    def to_dict(self) -> dict:
        return self.params

    @classmethod
    def from_dict(cls, params: dict) -> "Preprocessor":
        return cls(params)


# ══════════════════════════════════════════════════════════════════════════════
# 4. DATA GABUNGAN, BOBOT SPASIAL BLOK-DIAGONAL, SDWFCM, PENOMORAN
# ══════════════════════════════════════════════════════════════════════════════
def build_pooled(level_frames: Dict[str, pd.DataFrame], gdf_base) -> pd.DataFrame:
    """Data gabungan: satu baris per pasangan (grid, level) yang BUKAN Tergenang, untuk keempat
    level (urutan: level lalu id_grid). Kolom tambahan: id_grid_asli, level, cx, cy."""
    parts = []
    for lv in LEVELS:
        df = level_frames[lv["key"]]
        keep = df["tergenang"].values == 0
        part = df.loc[keep].copy()
        part.insert(1, "id_grid_asli", gdf_base["id_grid_asli"].values[keep])
        part.insert(2, "level", lv["key"])
        part["cx"] = gdf_base["cx"].values[keep]
        part["cy"] = gdf_base["cy"].values[keep]
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def block_knn_weights(coords: np.ndarray, groups: np.ndarray, knn: int,
                      sigma: Optional[float] = None) -> Tuple[csr_matrix, Dict[str, float]]:
    """Matriks bobot spasial blok-diagonal: KNN-`knn` dengan kernel Gaussian
    w_ij = exp(−d_ij² / 2σ²), dinormalisasi per baris (Σ_j W_ij = 1), dihitung HANYA di antara
    baris dengan `groups` sama (level yang sama). σ = median jarak ke tetangga dalam blok
    tersebut (bila tidak diberikan). Tidak ada tetangga lintas level."""
    n = len(coords)
    rows, cols, data, sigmas = [], [], [], {}
    for g in pd.unique(groups):
        idx = np.where(groups == g)[0]
        kk = min(knn + 1, len(idx))
        if kk < 2:
            continue
        nn = NearestNeighbors(n_neighbors=kk, algorithm="ball_tree").fit(coords[idx])
        d, j = nn.kneighbors(coords[idx])
        d, j = d[:, 1:], j[:, 1:]
        sg = float(sigma) if sigma else float(np.median(d))
        w = np.exp(-d ** 2 / (2.0 * sg ** 2))
        w /= w.sum(axis=1, keepdims=True)
        rows.append(np.repeat(idx, kk - 1))
        cols.append(idx[j].ravel())
        data.append(w.ravel())
        sigmas[str(g)] = sg
    W = csr_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    return W, sigmas


def block_adjacency(A_full: csr_matrix, grid_idx: np.ndarray, groups: np.ndarray) -> csr_matrix:
    """Ketetanggaan rook biner pada baris data gabungan: dua baris bertetangga ⇔ grid-nya
    bertetangga rook DAN berada pada level yang sama."""
    A = A_full[grid_idx][:, grid_idx].tocoo()
    same = groups[A.row] == groups[A.col]
    return csr_matrix((A.data[same], (A.row[same], A.col[same])), shape=A.shape)


def run_sdwfcm(X: np.ndarray, W: csr_matrix, k: int, cfg: Cfg, seeds: Optional[List[int]] = None,
               n_init: int = SDWFCM_N_INIT, alpha: Optional[float] = None,
               keep_runs: bool = False) -> dict:
    """SDWFCM multi-start dengan W yang sudah dihitung: beberapa inisialisasi acak (seed
    SDWFCM_SEED + i), dipilih J terkecil. `alpha=0` = FCM non-spasial."""
    t0 = time.time()
    seeds = list(seeds) if seeds else [SDWFCM_SEED + i for i in range(max(1, n_init))]
    a = cfg.sdwfcm_alpha if alpha is None else alpha
    best, runs = None, []
    for rs in seeds:
        t1 = time.time()
        model = SpatialDistanceWeightedFCM(
            k=k, m=cfg.sdwfcm_m, alpha=a, sigma=None, knn=cfg.sdwfcm_knn,
            max_iter=cfg.sdwfcm_max_iter, tol=cfg.sdwfcm_tol, rs=rs,
            impact_weight=cfg.sdwfcm_impact_weight,
        ).fit(X, W=W)
        J = float(model.objective_)
        runs.append({"seed": int(rs), "objective": J, "n_iter": int(model.n_iter_),
                     "time_sec": time.time() - t1, "labels": model.labels_.astype(int)})
        if best is None or J < best[0]:
            best = (J, rs, model)
    J, rs, model = best
    out = {
        "labels": model.labels_.astype(int),
        "U": model.U_,
        "max_membership": model.max_membership_,
        "centers": model.centers_,
        "objective": J,
        "seed": int(rs),
        "time": time.time() - t0,
        "time_per_init": float(np.mean([r["time_sec"] for r in runs])),
        "objectives": {r["seed"]: r["objective"] for r in runs},
    }
    if keep_runs:
        out["runs"] = runs
    return out


def relabel_by_metric(labels: np.ndarray, metric: np.ndarray) -> np.ndarray:
    """Penomoran ulang: klaster dengan rata-rata `metric` terendah → 0, dst.
    Seri dipecah dengan nomor lama (deterministik)."""
    labels = np.asarray(labels)
    uniq = sorted(int(c) for c in np.unique(labels) if c >= 0)
    means = {c: float(np.nanmean(metric[labels == c])) for c in uniq}
    order = sorted(uniq, key=lambda c: (means[c], c))
    mapping = {old: new for new, old in enumerate(order)}
    return np.array([mapping.get(int(l), int(l)) for l in labels], dtype=int)


def _permute(labels: np.ndarray, U: np.ndarray, mapping: Dict[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    """Terapkan pemetaan label lama → baru pada label dan kolom U."""
    new_labels = np.array([mapping[int(l)] for l in labels], dtype=int)
    new_U = np.zeros_like(U)
    for old, new in mapping.items():
        new_U[:, new] = U[:, old]
    return new_labels, new_U


def number_by_travel_time(labels: np.ndarray, U: np.ndarray, waktu_min: np.ndarray):
    """Aturan penomoran: urut naik rata-rata waktu_tes_min (menit, termasuk ruas snapping) pada
    data gabungan; klaster 0 = akses terbaik. Klaster kosong diletakkan terakhir."""
    k = U.shape[1]
    means = [float(waktu_min[labels == c].mean()) if np.any(labels == c) else np.inf for c in range(k)]
    order = sorted(range(k), key=lambda c: (means[c], c))
    return _permute(labels, U, {old: new for new, old in enumerate(order)})


def assign_to_centers(X: np.ndarray, W: csr_matrix, centers: np.ndarray, m: float, alpha: float,
                      max_iter: int = 150, tol: float = 1e-4) -> np.ndarray:
    """Keanggotaan SDWFCM dengan pusat klaster TETAP (dipakai simulasi blokir jalan di dashboard,
    bukan hasil skripsi): U diiterasi dengan d_t = (1 − α) d_a + α d_s sampai konvergen."""
    da = cdist(X, centers) ** 2 + 1e-10
    U = fuzzy_membership_update(da, m)
    for _ in range(max_iter):
        Um = U ** m
        ds = np.column_stack([(W @ (da[:, c] * Um[:, c])) / ((W @ Um[:, c]) + 1e-10)
                              for c in range(centers.shape[0])])
        Un = fuzzy_membership_update(np.clip((1 - alpha) * da + alpha * ds, 1e-10, None), m)
        diff = np.linalg.norm(Un - U)
        U = Un
        if diff < tol:
            break
    return U


# ══════════════════════════════════════════════════════════════════════════════
# 5. METRIK EVALUASI
# ══════════════════════════════════════════════════════════════════════════════
def rook_adjacency(w) -> csr_matrix:
    """Pola ketetanggaan (biner, simetris) dari libpysal W."""
    A = w.sparse.tocsr().copy()
    A.data[:] = 1.0
    A = ((A + A.T) > 0).astype(np.int8).tocsr()
    return A


def _centroids(X, labels, ks):
    return np.vstack([X[labels == c].mean(axis=0) for c in ks])


def wcss(X, labels) -> float:
    ks = sorted(set(labels.tolist()))
    C = _centroids(X, labels, ks)
    return float(sum(((X[labels == c] - C[i]) ** 2).sum() for i, c in enumerate(ks)))


def ketegasan_partisi(U: np.ndarray, X: Optional[np.ndarray] = None,
                      m: Optional[float] = None) -> float:
    """Ketegasan partisi = 1 − PE / ln K, dengan PE = partition entropy keanggotaan
    fuzzy (0 = keanggotaan merata, 1 = partisi tegas).

    Bila X dan m diberikan, keanggotaan dihitung ulang di ruang atribut
    (rumus FCM standar pada pusat fuzzy akhir, tanpa suku spasial)."""
    K = U.shape[1]
    if K < 2:
        return 0.0
    if X is not None and m is not None:
        d = cdist(X, fuzzy_centers(X, U, m)) ** 2 + 1e-10
        r = d[:, :, None] / d[:, None, :]
        U = 1.0 / (r ** (1.0 / (m - 1.0))).sum(axis=2)
        U = U / U.sum(axis=1, keepdims=True)
    pe = float(-(U * np.log(np.clip(U, 1e-12, None))).sum(axis=1).mean())
    return 1.0 - pe / np.log(K)


def fuzzy_centers(X, U, m: float) -> np.ndarray:
    Um = U ** m
    return (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)


def i_index(X, labels, p: int = IINDEX_P, centers: Optional[np.ndarray] = None) -> float:
    """I-Index (Maulik & Bandyopadhyay, 2002). `centers` = pusat klaster fuzzy
    SDWFCM (bila tersedia); tanpa itu dipakai centroid tegas."""
    ks = sorted(set(labels.tolist()))
    K = len(ks)
    C = centers[ks] if centers is not None else _centroids(X, labels, ks)
    E1 = float(np.linalg.norm(X - X.mean(axis=0), axis=1).sum())
    EK = float(sum(np.linalg.norm(X[labels == c] - C[i], axis=1).sum() for i, c in enumerate(ks)))
    DK = float(cdist(C, C).max()) if K > 1 else 0.0
    if EK <= 0:
        return 0.0
    return float(((1.0 / K) * (E1 / EK) * DK) ** p)


def dunn_index(X, labels, sample: int = DUNN_SAMPLE, rs: int = 42) -> float:
    """Dunn (1974): min jarak antaranggota klaster berbeda / max diameter klaster,
    pada satu sampel acak grid (seed rs) karena bentuk titik-ke-titik O(n²)."""
    n = len(X)
    idx = np.random.RandomState(rs).permutation(n)[:min(sample, n)]
    Xs, ls = X[idx], np.asarray(labels)[idx]
    D = cdist(Xs, Xs)
    same = ls[:, None] == ls[None, :]
    np.fill_diagonal(same, True)
    if (~same).sum() == 0:
        return 0.0
    diam = float(D[same].max())
    return float(D[~same].min() / diam) if diam > 0 else 0.0


def dunn_multi(X, labels, seeds=DUNN_SEEDS, sample: int = DUNN_SAMPLE) -> dict:
    """Dunn pada beberapa sampel acak (seed 42–46): rerata dan simpangan baku (ddof = 1)."""
    vals = [dunn_index(X, labels, sample=sample, rs=s) for s in seeds]
    return {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1)), "nilai": vals,
            "seeds": list(seeds), "ukuran_sampel": sample}


def silhouette_sampled(X, labels, sample: int = SILHOUETTE_SAMPLE, rs: int = SILHOUETTE_SEED) -> float:
    """Silhouette pada sampel acak (seed tetap) bila n > sample."""
    n = len(X)
    if n <= sample:
        return float(silhouette_score(X, labels))
    return float(silhouette_score(X, labels, sample_size=sample, random_state=rs))


def _spatial_blocks(labels: np.ndarray, A: csr_matrix) -> np.ndarray:
    """Blok spasial = komponen terhubung (rook) dari grid pada klaster yang sama."""
    coo = A.tocoo()
    same = labels[coo.row] == labels[coo.col]
    B = csr_matrix((np.ones(same.sum()), (coo.row[same], coo.col[same])), shape=A.shape)
    _, comp = connected_components(B, directed=False)
    return comp


def desc_pesc(X, labels, A: csr_matrix, coords: np.ndarray) -> Tuple[float, float]:
    """DESC & PESC (Guo dkk., 2015), blok spasial dari ketetanggaan ROOK `A`.

    DESC = Σ_i V_i² / d_i²      (blok berukuran ≥ 2)
    PESC = Σ_k Σ_{i<j} V_i V_j / (D_ij · d_ij · B_nk)
    V_i  = proporsi ukuran blok terhadap klaster, d_i = rata-rata jarak atribut
    anggota ke pusat blok, D_ij = jarak spasial (km) antar pusat blok,
    d_ij = jarak atribut antar pusat blok, B_nk = jumlah blok klaster k.
    """
    comp = _spatial_blocks(labels, A)
    df = pd.DataFrame({"comp": comp, "lab": labels})
    sizes = df.groupby("comp").size()
    lab_of = df.groupby("comp")["lab"].first()
    cl_size = df.groupby("lab").size()

    n_attr = X.shape[1]
    Xs = pd.DataFrame(X).groupby(comp).mean()
    Cs = pd.DataFrame(coords).groupby(comp).mean()

    desc = 0.0
    Xc = Xs.values[comp]
    member_dist = np.linalg.norm(X - Xc, axis=1)
    d_mean = pd.Series(member_dist).groupby(comp).mean()
    for blk in sizes.index:
        V = sizes[blk] / cl_size[lab_of[blk]]
        d = float(d_mean[blk])
        if sizes[blk] >= 2 and d > 1e-9:
            desc += V ** 2 / d ** 2

    pesc = 0.0
    for lab, blks in lab_of.groupby(lab_of):
        idx = blks.index.values
        Bn = len(idx)
        if Bn < 2:
            continue
        V = (sizes[idx] / cl_size[lab]).values
        P = Xs.loc[idx].values[:, :n_attr]
        Q = Cs.loc[idx].values / 1000.0          # meter → km
        if Bn > 3000:                            # batasi pasangan: 3.000 blok terbesar
            top = np.argsort(-V)[:3000]
            V, P, Q = V[top], P[top], Q[top]
        for s in range(0, len(V), 500):
            D = cdist(Q[s:s + 500], Q)
            dA = cdist(P[s:s + 500], P)
            VV = np.outer(V[s:s + 500], V)
            iu = np.arange(s, min(s + 500, len(V)))[:, None] < np.arange(len(V))[None, :]
            denom = D * dA * Bn
            valid = iu & (denom > 1e-12)
            pesc += float((VV[valid] / denom[valid]).sum())
    return float(desc), float(pesc)


def same_label_neighbor_share(labels, A: csr_matrix) -> float:
    """Proporsi pasangan tetangga (A simetris, tiap pasangan dihitung sekali) yang berlabel sama.
    Tidak bergantung pada penomoran label."""
    coo = A.tocoo()
    upper = coo.row < coo.col
    r, c = coo.row[upper], coo.col[upper]
    labels = np.asarray(labels)
    return float((labels[r] == labels[c]).mean()) if len(r) else float("nan")


def size_entropy(labels) -> float:
    labels = np.asarray(labels)
    p = pd.Series(labels[labels >= 0]).value_counts(normalize=True).values
    return float(-(p * np.log(p + 1e-12)).sum())


def largest_cluster_share(labels) -> float:
    labels = np.asarray(labels)
    return float(np.bincount(labels[labels >= 0]).max() / (labels >= 0).sum() * 100)


def moran_labels(labels, w, permutations: int = MORAN_PERMUTATIONS) -> Tuple[Optional[float], Optional[float]]:
    """Moran's I pada label klaster (p-value pseudo dengan seed permutasi tetap)."""
    try:
        np.random.seed(MORAN_PERMUTATION_SEED)
        mi = Moran(np.asarray(labels).astype(float), w, permutations=permutations)
        return float(mi.I), float(mi.p_sim)
    except Exception as e:
        logger.warning(f"[moran_labels] gagal: {e}")
        return None, None


def partition_coefficients(U: np.ndarray) -> dict:
    """Koefisien partisi PC = (1/N) Σ_i Σ_k u_ik² dan entropi partisi PE = −(1/N) Σ_i Σ_k u_ik ln u_ik
    (Bezdek), pada keanggotaan akhir algoritma."""
    U = np.clip(np.asarray(U, float), 1e-12, None)
    return {"pc": float((U ** 2).sum(axis=1).mean()), "pe": float(-(U * np.log(U)).sum(axis=1).mean())}


def cdvm_distribution(states_a, states_b, n_states: int) -> float:
    """CDVM: total variation distance ½ Σ_s |p_s(b) − p_s(a)| antara distribusi state dua level."""
    pa = np.bincount(states_a, minlength=n_states) / len(states_a)
    pb = np.bincount(states_b, minlength=n_states) / len(states_b)
    return float(0.5 * np.abs(pb - pa).sum())


# ══════════════════════════════════════════════════════════════════════════════
# 6. PEMILIHAN K BERBASIS STABILITAS (data gabungan)
# ══════════════════════════════════════════════════════════════════════════════
K_SCORE_METRICS = ["iidx", "dunn", "desc", "ketegasan_partisi"]   # skor komposit lama (sensitivitas)


def subsample_masks(ids: np.ndarray, B: int, frac: float = SUBSAMPLE_FRAC,
                    seed0: int = SUBSAMPLE_SEED) -> List[np.ndarray]:
    """B subsampel: 80% id_grid unik dipilih tanpa pengembalian (seed seed0 + b); semua baris
    (level) dari grid terpilih ikut masuk."""
    uniq = np.unique(ids)
    n_sub = int(round(frac * len(uniq)))
    out = []
    for b in range(B):
        chosen = np.random.RandomState(seed0 + b).choice(uniq, size=n_sub, replace=False)
        out.append(np.isin(ids, chosen))
    return out


def composite_scores(df: pd.DataFrame, metrics: List[str]) -> pd.Series:
    """Skor komposit lama: rerata percentile rank metrik (besar = baik) + parsimoni linear."""
    ranks = [df[c].rank(pct=True) for c in metrics]
    kmin, kmax = df["k"].min(), df["k"].max()
    pars = 1.0 - (df["k"] - kmin) / max(kmax - kmin, 1)
    return pd.concat(ranks + [pars], axis=1).mean(axis=1)


def evaluate_k_stability(X: np.ndarray, W: csr_matrix, pool: pd.DataFrame, A_pool: csr_matrix,
                         cfg: Cfg, k_range=K_RANGE, B: int = SUBSAMPLE_B) -> Tuple[List[dict], dict, dict]:
    """Pemilihan K pada data gabungan (aturan ditetapkan sebelum melihat hasil).

    (a) stabilitas inisialisasi: 10 run (seed 42–51), rerata ARI berpasangan antar-run;
    (b) stabilitas subsampel: B subsampel 80% id_grid, tiap subsampel 3 inisialisasi (seed 42–44)
        diambil J terkecil; ARI terhadap solusi data penuh (J terkecil dari (a)) pada baris yang
        beririsan; rerata dan simpangan baku.
    K terpilih = K dengan rerata ARI subsampel tertinggi; bila beberapa K berselisih ≤ 0,01 dari
    nilai tertinggi, dipilih K terkecil di antaranya. Metrik pendukung hanya dilaporkan.
    Returns: (rows, ringkasan, solusi_penuh_per_K)
    """
    coords = pool[["cx", "cy"]].values
    groups = pool["level"].values
    masks = subsample_masks(pool["id_grid"].values, B)
    sub_W = [block_knn_weights(coords[mk], groups[mk], cfg.sdwfcm_knn)[0] for mk in masks]
    rows, solutions = [], {}
    for k in k_range:
        t0 = time.time()
        full = run_sdwfcm(X, W, k, cfg, seeds=STABILITY_SEEDS, keep_runs=True)
        labs = [r["labels"] for r in full["runs"]]
        ari_init = [adjusted_rand_score(a, b) for a, b in combinations(labs, 2)]
        t_init = time.time() - t0
        t1 = time.time()
        ari_sub, sub_seeds = [], []
        for mk, Wb in zip(masks, sub_W):
            r = run_sdwfcm(X[mk], Wb, k, cfg, n_init=SUBSAMPLE_N_INIT)
            ari_sub.append(adjusted_rand_score(full["labels"][mk], r["labels"]))
            sub_seeds.append(r["seed"])
        t_sub = time.time() - t1
        t2 = time.time()
        labels = full["labels"]
        desc, pesc = desc_pesc(X, labels, A_pool, coords)
        dn = dunn_multi(X, labels)
        row = {
            "k": k,
            "ari_subsampel_mean": float(np.mean(ari_sub)),
            "ari_subsampel_sd": float(np.std(ari_sub, ddof=1)),
            "ari_subsampel": [float(v) for v in ari_sub],
            "ari_inisialisasi_mean": float(np.mean(ari_init)),
            "ari_inisialisasi_sd": float(np.std(ari_init, ddof=1)),
            "seed_terbaik": full["seed"],
            "objective": full["objective"],
            "objective_per_seed": {str(s): v for s, v in full["objectives"].items()},
            "seed_terbaik_subsampel": sub_seeds,
            "iidx": i_index(X, labels, centers=fuzzy_centers(X, full["U"], cfg.sdwfcm_m)),
            "dunn": dn["mean"],
            "dunn_sd": dn["sd"],
            "ketegasan_partisi": ketegasan_partisi(full["U"], X, cfg.sdwfcm_m),
            "desc": desc,
            "pesc": pesc,
            "silhouette": silhouette_sampled(X, labels),
            "size_entropy": size_entropy(labels),
            "klaster_terbesar_persen": largest_cluster_share(labels),
            "time_sec": time.time() - t0,
            "waktu_inisialisasi_sec": t_init,
            "waktu_subsampel_sec": t_sub,
            "waktu_metrik_sec": time.time() - t2,
        }
        logger.info(f"[K={k}] ARI subsampel={row['ari_subsampel_mean']:.4f}±{row['ari_subsampel_sd']:.4f} "
                    f"ARI init={row['ari_inisialisasi_mean']:.4f} IIdx={row['iidx']:.3f} "
                    f"Dunn={row['dunn']:.4f} DESC={row['desc']:.3f} Sil={row['silhouette']:.3f} "
                    f"({row['time_sec']:.0f} s)")
        rows.append(row)
        solutions[k] = {key: full[key] for key in ("labels", "U", "centers", "objective", "seed",
                                                    "time", "time_per_init")}

    df = pd.DataFrame(rows)
    comp_desc = composite_scores(df, K_SCORE_METRICS)
    comp_nodesc = composite_scores(df, [c for c in K_SCORE_METRICS if c != "desc"])
    for row, a, b in zip(rows, comp_desc, comp_nodesc):
        row["komposit_dengan_desc"] = float(a)
        row["komposit_tanpa_desc"] = float(b)

    best = float(df["ari_subsampel_mean"].max())
    cands = df.loc[df["ari_subsampel_mean"] >= best - K_ARI_TOLERANCE, "k"].astype(int).tolist()
    k_sel = int(min(cands))
    ordered = df.sort_values(["ari_subsampel_mean", "k"], ascending=[False, True])
    runner = ordered[ordered["k"] != k_sel].iloc[0]
    summary = {
        "k_terpilih": k_sel,
        "ari_subsampel_tertinggi": best,
        "k_ari_tertinggi": int(ordered.iloc[0]["k"]),
        "k_dalam_toleransi": cands,
        "toleransi": K_ARI_TOLERANCE,
        "k_runner_up": int(runner["k"]),
        "ari_runner_up": float(runner["ari_subsampel_mean"]),
        "selisih_ari_terpilih_vs_runner_up": float(
            df.loc[df["k"] == k_sel, "ari_subsampel_mean"].iloc[0] - runner["ari_subsampel_mean"]),
        "k_komposit_dengan_desc": int(df.loc[comp_desc.idxmax(), "k"]),
        "k_komposit_tanpa_desc": int(df.loc[comp_nodesc.idxmax(), "k"]),
        "B": B,
        "fraksi_subsampel": SUBSAMPLE_FRAC,
        "n_init_subsampel": SUBSAMPLE_N_INIT,
        "seed_subsampel": [SUBSAMPLE_SEED + b for b in range(B)],
        "seed_inisialisasi": STABILITY_SEEDS,
        "aturan": ("K dengan rerata ARI subsampel tertinggi; bila beberapa K berselisih ≤ 0,01 dari "
                   "nilai tertinggi, dipilih K terkecil di antaranya. Metrik pendukung dan skor "
                   "komposit lama hanya dilaporkan."),
    }
    return rows, summary, solutions


# ══════════════════════════════════════════════════════════════════════════════
# 7. PERBANDINGAN ALGORITMA (level Baseline, data non-Tergenang = semua grid)
# ══════════════════════════════════════════════════════════════════════════════
def compare_algorithms(X: np.ndarray, W: csr_matrix, w_rook, A_rook: csr_matrix, k: int,
                       waktu_min: np.ndarray, cfg: Cfg) -> List[dict]:
    """FCM (α = 0), SFCM, SDWFCM (masing-masing 10 inisialisasi, J terkecil, m sama = cfg.sdwfcm_m),
    REDCAP, SKATER. Semua memakai praproses, K, dan aturan penomoran yang sama (urut rata-rata
    waktu_tes_min). Untuk algoritma fuzzy dilaporkan koefisien partisi (PC) dan entropi partisi (PE)
    dari keanggotaan akhir. Partisi dengan klaster terbesar > 90% grid ditandai degeneratif."""
    import copy
    runs = {}

    fcm = run_sdwfcm(X, W, k, cfg, alpha=0.0)
    runs["FCM"] = {"labels": fcm["labels"], "time_per_init": fcm["time_per_init"], "n_init": SDWFCM_N_INIT,
                   "seed_terbaik": fcm["seed"], "objective": fcm["objective"], "U": fcm["U"], "m": cfg.sdwfcm_m}

    op = neighbor_mean_operator(w_rook, len(X))
    best, times = None, []
    for rs in [SDWFCM_SEED + i for i in range(SDWFCM_N_INIT)]:
        t0 = time.time()
        sf = SpatialFuzzyCMeans(k=k, m=cfg.sdwfcm_m, alpha=cfg.sfcm_alpha, max_iter=cfg.sfcm_max_iter,
                                tol=cfg.sfcm_tol, rs=rs).fit(X, w_rook, operator=op)
        times.append(time.time() - t0)
        if best is None or sf.objective_ < best.objective_:
            best = sf
    runs["SFCM"] = {"labels": best.labels_.astype(int), "time_per_init": float(np.mean(times)),
                    "n_init": SDWFCM_N_INIT, "seed_terbaik": int(best.rs), "objective": best.objective_,
                    "U": best.U_, "m": best.m}

    sd = run_sdwfcm(X, W, k, cfg)
    runs["SDWFCM"] = {"labels": sd["labels"], "time_per_init": sd["time_per_init"], "n_init": SDWFCM_N_INIT,
                      "seed_terbaik": sd["seed"], "objective": sd["objective"], "U": sd["U"], "m": cfg.sdwfcm_m}

    t0 = time.time()
    try:
        rc = REDCAPManual(X, copy.deepcopy(w_rook), k=k, linkage=cfg.redcap_linkage,
                          size_alpha=cfg.size_alpha, net_dist=waktu_min,
                          iso_pen=cfg.isolation_penalty_weight, iso_thr=cfg.isolation_time_threshold)
        rc.solve()
        runs["REDCAP"] = {"labels": np.asarray(rc.labels_, dtype=int), "time_per_init": time.time() - t0,
                          "n_init": 1}
    except Exception as e:
        runs["REDCAP"] = {"error": f"{type(e).__name__}: {e}", "time_per_init": time.time() - t0, "n_init": 1}

    t0 = time.time()
    try:
        runs["SKATER"] = {"labels": run_skater(A_rook, X, k, cfg), "time_per_init": time.time() - t0,
                          "n_init": 1}
    except Exception as e:
        logger.warning(f"[SKATER] gagal: {type(e).__name__}: {e}")
        runs["SKATER"] = {"error": f"{type(e).__name__}: {e}", "time_per_init": time.time() - t0, "n_init": 1}

    rows = []
    for algo, r in runs.items():
        base = {"algoritma": algo, "n_init": r["n_init"], "time_per_init_sec": float(r["time_per_init"])}
        if "error" in r:
            rows.append({**base, "status": "gagal", "layak_dibandingkan": False, "galat": r["error"]})
            continue
        labels = relabel_by_metric(r["labels"], waktu_min)
        big = largest_cluster_share(labels)
        n_cl = int(len(np.unique(labels)))
        degenerate = big > DEGENERATE_MAX_SHARE * 100
        row = {**base,
               "status": "degeneratif" if degenerate else "ok",
               "layak_dibandingkan": not degenerate,
               "n_cluster": n_cl,
               "klaster_terbesar_persen": big,
               "size_entropy": size_entropy(labels),
               "seed_terbaik": r.get("seed_terbaik"),
               "objective": r.get("objective"),
               "m": r.get("m")}
        if r.get("U") is not None:
            row.update(partition_coefficients(r["U"]))
        if n_cl >= 2:
            mi, mp = moran_labels(labels, w_rook)
            row.update({
                "silhouette": float(silhouette_score(X, labels)),
                "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
                "davies_bouldin": float(davies_bouldin_score(X, labels)),
                "moran_i": mi, "moran_p": mp, "moran_permutasi": MORAN_PERMUTATIONS,
                "proporsi_tetangga_sama": same_label_neighbor_share(labels, A_rook),
            })
        rows.append(row)
        logger.info(f"[compare] {algo}: status={row['status']} sil={row.get('silhouette')} "
                    f"terbesar={big:.1f}% t/init={row['time_per_init_sec']:.1f}s")
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 8. PROFIL KLASTER (data gabungan) DAN DISTRIBUSI TIPOLOGI PER LEVEL
# ══════════════════════════════════════════════════════════════════════════════
PROFILE_COLS = (
    ["Road_Density_mean", SKENARIO]
    + ["waktu_tes_pendidikan", "waktu_tes_kesehatan", "waktu_tes_pemerintahan",
       "waktu_tes_ibadah", "waktu_tes_gor", "waktu_tes_min", "jumlah_opsi_rute", "is_isolated"]
    + ["is_isolated_pendidikan", "is_isolated_kesehatan", "is_isolated_pemerintahan",
       "is_isolated_ibadah", "is_isolated_gor"]
)


TIME_COLS = ["waktu_tes_pendidikan", "waktu_tes_kesehatan", "waktu_tes_pemerintahan",
             "waktu_tes_ibadah", "waktu_tes_gor", "waktu_tes_min"]


def rank_label(c: int, k: int) -> str:
    """Label peringkat (Putaran 4; penyajian, bukan perubahan model): klaster diurutkan naik menurut
    rata-rata waktu_tes_min, sehingga klaster c = "Tipologi c+1"; 1 = terbaik, K = terburuk."""
    if c == 0:
        return "Tipologi 1 (terbaik)"
    if c == k - 1:
        return f"Tipologi {k} (terburuk)"
    return f"Tipologi {c + 1}"


def cluster_profile(df: pd.DataFrame, labels: np.ndarray, k: int, t_pen: float) -> List[dict]:
    """Profil klaster pada data gabungan: rerata semua variabel profil; untuk variabel waktu juga
    median, P25, P75, P90; jumlah dan persentase baris bernilai penalti (per kategori dan waktu
    minimum); proporsi baris dengan waktu minimum > batas waktu evakuasi (dan nilai sensitivitas);
    proporsi baris Terputus (waktu minimum = penalti); proporsi grid terisolasi; label peringkat.
    Kelas bahaya banjir = variabel deskriptif (bukan fitur)."""
    rows = []
    n = len(labels)
    for c in range(k):
        sel = labels == c
        m = int(sel.sum())
        row = {"klaster": c, "jumlah_baris": m, "persen_baris": float(m / n * 100)}
        for col in PROFILE_COLS:
            row[col] = float(df.loc[sel, col].mean()) if m else None
        for col in TIME_COLS:
            v = df.loc[sel, col].values.astype(float)
            q = np.percentile(v, [50, 25, 75, 90]) if m else [None] * 4
            (row[f"{col}_median"], row[f"{col}_p25"], row[f"{col}_p75"],
             row[f"{col}_p90"]) = (float(x) if m else None for x in q)
            pen = int((v >= t_pen - 1e-9).sum()) if m else 0
            row[f"{col}_n_penalti"] = pen
            row[f"{col}_persen_penalti"] = float(pen / m * 100) if m else None
        wmin = df.loc[sel, "waktu_tes_min"].values.astype(float)
        for thr in (EVAC_TIME_MIN,) + tuple(EVAC_TIME_SENS):
            row[f"proporsi_waktu_min_lebih_{thr:g}"] = float((wmin > thr).mean()) if m else None
        row["proporsi_waktu_min_lebih_batas"] = row[f"proporsi_waktu_min_lebih_{EVAC_TIME_MIN:g}"]
        row["proporsi_terputus"] = float((wmin >= t_pen - 1e-9).mean()) if m else None
        row["proporsi_terisolasi"] = float(df.loc[sel, "is_isolated"].mean()) if m else None
        row["deskripsi"] = rank_label(c, k)
        rows.append(row)
    return rows


def crosstab_labels(a: np.ndarray, b: np.ndarray, ka: int, kb: int) -> dict:
    """Tabulasi silang label dua model pada baris yang sama (baris = model a, kolom = model b)."""
    M = np.zeros((ka, kb), dtype=int)
    np.add.at(M, (np.asarray(a), np.asarray(b)), 1)
    return {"matrix": M.tolist(), "baris": [f"K{ka}-{i}" for i in range(ka)],
            "kolom": [f"K{kb}-{j}" for j in range(kb)],
            "ari": float(adjusted_rand_score(a, b))}


def access_category(waktu_min: np.ndarray, tergenang: np.ndarray, t_pen: float,
                    threshold: float = EVAC_TIME_MIN) -> np.ndarray:
    """Kategori akses per grid (padanan Li dkk. 2026, hlm. 2919; tidak mengubah klasterisasi):
    3 = Tergenang (flooded), 2 = Terputus (isolated: waktu minimum = penalti),
    1 = Jauh (remote: terhubung, waktu minimum > threshold), 0 = Terjangkau (≤ threshold)."""
    w = np.asarray(waktu_min, float)
    wet = np.asarray(tergenang, bool)
    cut = w >= t_pen - 1e-9
    return np.select([wet, cut, w > threshold], [3, 2, 1], default=0).astype(int)


def access_summary(cat: np.ndarray) -> dict:
    n = len(cat)
    cnt = np.bincount(cat, minlength=4)
    return {AKSES_STATUS[c]: {"jumlah_grid": int(cnt[c]), "persen": float(cnt[c] / n * 100)} for c in range(4)}


def access_transition(a: np.ndarray, b: np.ndarray) -> dict:
    """Matriks transisi kategori akses 4 × 4 (urutan AKSES_STATUS) antar dua level."""
    M = np.zeros((4, 4), dtype=int)
    np.add.at(M, (np.asarray(a), np.asarray(b)), 1)
    return {"matrix": M.tolist(), "state_labels": [AKSES_STATUS[c] for c in range(4)],
            "tetap": int(np.trace(M)), "berubah": int(M.sum() - np.trace(M))}


def tas_change(status_base: np.ndarray, status_level: np.ndarray) -> dict:
    """Perubahan TAS terhadap Baseline (aturan utama).
    TAS baru akibat banjir = bukan TAS di Baseline dan TAS di level ini.
    TAS hilang = TAS di Baseline dan bukan TAS di level ini, dipecah menurut status di level ini."""
    b, l = np.asarray(status_base), np.asarray(status_level)
    new = (b != 1) & (l == 1)
    lost = (b == 1) & (l != 1)
    return {
        "tas_baru": int(new.sum()),
        "tas_baru_dari_status_baseline": {TAS_STATUS[c]: int((new & (b == c)).sum()) for c in (0, 2)},
        "tas_hilang": int(lost.sum()),
        "tas_hilang_jadi_tergenang": int((lost & (l == 3)).sum()),
        "tas_hilang_jadi_tes_terdekat_tidak_terjangkau": int((lost & (l == 2)).sum()),
        "tas_hilang_lainnya": int((lost & (l == 0)).sum()),
        "tas_tetap": int(((b == 1) & (l == 1)).sum()),
    }


def level_distribution(states: np.ndarray, k: int) -> List[dict]:
    """Distribusi state satu level: jumlah grid per tipologi dan Tergenang (state k)."""
    n = len(states)
    cnt = np.bincount(states, minlength=k + 1)
    non = int(cnt[:k].sum())
    out = [{"state": int(c), "nama": f"Klaster {c}", "jumlah_grid": int(cnt[c]),
            "persen_semua_grid": float(cnt[c] / n * 100),
            "persen_non_tergenang": float(cnt[c] / non * 100) if non else None} for c in range(k)]
    out.append({"state": k, "nama": TERGENANG, "jumlah_grid": int(cnt[k]),
                "persen_semua_grid": float(cnt[k] / n * 100), "persen_non_tergenang": None})
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 9. ANALISIS TRANSISI DENGAN STATE TERGENANG
# ══════════════════════════════════════════════════════════════════════════════
TRANSITION_PAIRS = [("baseline", "rendah"), ("rendah", "sedang"), ("sedang", "tinggi"),
                    ("baseline", "tinggi")]


def transition_analysis(states_from: np.ndarray, states_to: np.ndarray, k: int) -> dict:
    """Transisi antar dua level. State: 0..K−1 = tipologi, K = Tergenang.

    - matriks (K+1) × (K+1) jumlah grid;
    - grid yang masuk Tergenang (non-Tergenang → Tergenang), jumlah dan persentase;
    - stability rate dan ARI HANYA pada grid non-Tergenang di kedua level;
    - transisi dominan di luar diagonal (menuju Tergenang atau tipologi lain);
    - active edges = jumlah sel di luar diagonal yang > 0;
    - CDVM = total variation distance distribusi state (K+1 state).
    """
    a, b = np.asarray(states_from), np.asarray(states_to)
    S = k + 1
    M = np.zeros((S, S), dtype=int)
    np.add.at(M, (a, b), 1)
    both = (a < k) & (b < k)
    Mt = M[:k, :k]
    into = int(((a < k) & (b == k)).sum())
    out_of = int(((a == k) & (b < k)).sum())
    off = M.copy()
    np.fill_diagonal(off, 0)
    dom = np.unravel_index(int(off.argmax()), off.shape) if off.sum() > 0 else None
    n = len(a)
    return {
        "matrix": M.tolist(),
        "state_labels": [f"Klaster {c}" for c in range(k)] + [TERGENANG],
        "n_grid": int(n),
        "masuk_tergenang": into,
        "persen_masuk_tergenang_semua_grid": float(into / n * 100),
        "persen_masuk_tergenang_dari_non_tergenang_awal": float(into / (a < k).sum() * 100) if (a < k).any() else None,
        "keluar_tergenang": out_of,
        "n_non_tergenang_kedua_level": int(both.sum()),
        "stability_rate": float(np.trace(Mt) / Mt.sum() * 100) if Mt.sum() else None,
        "ari": float(adjusted_rand_score(a[both], b[both])) if both.sum() > 1 else None,
        "dominant_transition": None if dom is None else {
            "from": int(dom[0]), "to": int(dom[1]), "count": int(off[dom]),
            "menuju": TERGENANG if dom[1] == k else "tipologi lain"},
        "active_edges": int((off > 0).sum()),
        "active_edges_antar_tipologi": int((off[:k, :k] > 0).sum()),
        "n_berpindah": int(off.sum()),
        "cdvm": cdvm_distribution(a, b, S),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 10. DETEKSI TITIK AMAN SEMU — DETOUR INDEX (Subbab 3.2.11)
# ══════════════════════════════════════════════════════════════════════════════
def _graph_to_csr(G: nx.Graph, nl: np.ndarray) -> csr_matrix:
    return graph_csr(G, nl)


def detect_tas_detour(
    df: pd.DataFrame,
    grid_xy: np.ndarray,
    tes_v: Optional[gpd.GeoDataFrame],
    graph_pack: tuple,
    t_pen: float,
    cfg: Cfg,
    max_snap: float = 300.0,
    tergenang: Optional[np.ndarray] = None,
) -> dict:
    """Deteksi Titik Aman Semu berbasis Detour Index waktu.

    T_ideal = max(d_Euclid(centroid, TES terdekat), TAS_MIN_EUCLID_M) / kecepatan
    T_aktual = [ruas snapping centroid → simpul + jarak jaringan antarsimpul
                + ruas snapping simpul → titik TES] / kecepatan, ke TES yang SAMA
               (snapping ≤ max_snap), sehingga T_ideal dan T_aktual sama-sama mengukur
               perjalanan centroid → titik TES. Batas minimum TAS_MIN_EUCLID_M (50 m) dipasang
               pada KEDUA jarak, sehingga T_aktual ≥ T_ideal untuk semua grid terjangkau
    DI_t = T_aktual / T_ideal
    Grid Tergenang (mask simulasi level ini) → status "Tergenang", dikeluarkan dari seluruh
    perhitungan TAS. Grid non-Tergenang dengan T_aktual = T_pen → "TES terdekat tidak terjangkau".
    Untuk grid non-Tergenang yang terjangkau (R):
        aturan utama      : TAS ⇔ DI_t ≥ TAS_DI_ABSOLUTE (2) ∧ T_ideal ≤ TAS_T_IDEAL_MAX (5 menit)
        sensitivitas      : TAS ⇔ T_ideal ≤ P25(T_ideal | R) ∧ DI_t ≥ P75(DI_t | R)
    status (aturan utama) dan status_persentil: 0 = Non-TAS, 1 = TAS, 2 = TES terdekat tidak terjangkau,
    3 = Tergenang.
    Kategori TES terdekat = kategori TES valid terdekat secara Euclidean (e(i)).
    """
    n = len(grid_xy)
    speed = cfg.walking_speed_m_per_min
    G, nl, tn = graph_pack
    wet = np.zeros(n, bool) if tergenang is None else np.asarray(tergenang, bool)

    if tes_v is None or len(tes_v) == 0 or tn is None or len(nl) == 0:
        st = np.where(wet, 3, 2).astype(int)
        return {"t_ideal": np.full(n, np.nan), "t_aktual": np.full(n, t_pen),
                "detour_index": np.full(n, np.nan), "is_tas": np.zeros(n, int),
                "status": st, "status_persentil": st.copy(), "kategori_tes_terdekat": np.full(n, None),
                "summary": {"jumlah_tes_terdekat_tidak_terjangkau": int((~wet).sum()), "jumlah_tergenang": int(wet.sum())}}

    tes_xy = np.column_stack([tes_v.geometry.x.values, tes_v.geometry.y.values])
    d_euc_raw, tes_idx = cKDTree(tes_xy).query(grid_xy, k=1)
    d_euc = np.maximum(d_euc_raw, TAS_MIN_EUCLID_M)
    t_ideal = d_euc / speed

    csr = _graph_to_csr(G, nl)
    g_snap_d, g_node = tn.query(grid_xy, k=1)
    t_snap_d, t_node = tn.query(tes_xy, k=1)
    grid_ok = g_snap_d <= max_snap
    tes_ok = t_snap_d <= max_snap

    net = np.full(n, np.inf)
    cand = np.where(grid_ok & tes_ok[tes_idx])[0]
    src_nodes = t_node[tes_idx[cand]]
    uniq_src = np.unique(src_nodes)

    def _solve(sources, targets_by_src, limit):
        unresolved = []
        for s_ in range(0, len(sources), 32):
            batch = sources[s_:s_ + 32]
            D = dijkstra(csr, directed=False, indices=batch, limit=limit)
            for bi, src in enumerate(batch):
                gi = targets_by_src[src]
                vals = D[bi, g_node[gi]]
                net[gi] = vals
                if np.isinf(vals).any():
                    unresolved.append(src)
        return unresolved

    targets = pd.Series(cand).groupby(src_nodes).apply(lambda v: v.values).to_dict()
    pending = _solve(uniq_src, targets, limit=8000.0)
    if pending:
        _solve(np.array(pending), targets, limit=t_pen * speed)

    t_akt = np.full(n, float(t_pen))
    fin = np.isfinite(net)
    total_m = g_snap_d + net + t_snap_d[tes_idx]          # ruas snapping + jaringan
    total_m = np.maximum(total_m, TAS_MIN_EUCLID_M)        # batas minimum yang sama dengan T_ideal
    t_akt[fin] = np.minimum(total_m[fin] / speed, t_pen)
    reach = (t_akt < t_pen) & ~wet              # non-Tergenang & terjangkau
    cut = (t_akt >= t_pen) & ~wet               # non-Tergenang, TES terdekat tidak terjangkau
    di = np.full(n, np.nan)
    di[reach] = t_akt[reach] / t_ideal[reach]
    kat = tes_v["kategori"].values[tes_idx] if "kategori" in tes_v.columns else np.full(n, None)

    # aturan utama (Putaran 4): DI ≥ 2, T_ideal ≤ 5 menit, T_aktual ≥ batas waktu evakuasi
    base_rule = reach & (di >= TAS_DI_ABSOLUTE) & (t_ideal <= TAS_T_IDEAL_MAX)
    is_tas = base_rule & (t_akt >= TAS_T_AKTUAL_MIN)
    status = np.select([wet, cut, is_tas], [3, 2, 1], default=0).astype(int)
    # sensitivitas ambang T_aktual (20 dan 40 menit) dan aturan absolut v3 (tanpa syarat T_aktual)
    sens_waktu = {}
    for thr in EVAC_TIME_SENS:
        m = base_rule & (t_akt >= thr)
        sens_waktu[f"{thr:g}"] = {
            "ambang_t_aktual_menit": thr,
            "jumlah_tas": int(m.sum()),
            "persen_tas_non_tergenang": float(m.sum() / (~wet).sum() * 100) if (~wet).any() else None,
            "jumlah_tas_utama_yang_tetap_tas": int((is_tas & m).sum()),
            "proporsi_tas_utama_yang_tetap_tas": float((is_tas & m).sum() / is_tas.sum()) if is_tas.any() else None,
        }
    # sensitivitas (persentil, aturan v2)
    p25 = float(np.percentile(t_ideal[reach], 25))
    p75 = float(np.percentile(di[reach], 75))
    is_tas_p = reach & (t_ideal <= p25) & (di >= p75)
    status_p = np.select([wet, cut, is_tas_p], [3, 2, 1], default=0).astype(int)

    non = reach & ~is_tas
    n_reach = int(reach.sum())
    n_dry = int((~wet).sum())
    summary = {
        "aturan": (f"DI_t ≥ {TAS_DI_ABSOLUTE:g}, T_ideal ≤ {TAS_T_IDEAL_MAX:g} menit, dan T_aktual ≥ "
                   f"{TAS_T_AKTUAL_MIN:g} menit (grid non-Tergenang terjangkau)"),
        "jumlah_tas": int(is_tas.sum()),
        "jumlah_non_tas": int(non.sum()),
        "jumlah_tes_terdekat_tidak_terjangkau": int(cut.sum()),
        "jumlah_tergenang": int(wet.sum()),
        "jumlah_terjangkau": n_reach,
        "jumlah_non_tergenang": n_dry,
        "persen_tas": float(is_tas.sum() / n * 100),
        "persen_tas_non_tergenang": float(is_tas.sum() / n_dry * 100) if n_dry else None,
        "persen_tas_terjangkau": float(is_tas.sum() / n_reach * 100) if n_reach else None,
        "persen_tes_terdekat_tidak_terjangkau": float(cut.sum() / n * 100),
        "persen_tergenang": float(wet.sum() / n * 100),
        "sebaran_di_tas": _quantiles(di[is_tas]),
        "sebaran_di_non_tas": _quantiles(di[non]),
        "median_t_ideal_tas": float(np.median(t_ideal[is_tas])) if is_tas.any() else None,
        "median_t_aktual_tas": float(np.median(t_akt[is_tas])) if is_tas.any() else None,
        "tas_per_kategori_tes_terdekat": {str(k): int(v) for k, v in
                                           pd.Series(kat[is_tas]).value_counts().sort_index().items()},
        "sensitivitas_ambang_waktu": sens_waktu,
        "sensitivitas_absolut_v3": {
            "aturan": f"DI_t ≥ {TAS_DI_ABSOLUTE:g} dan T_ideal ≤ {TAS_T_IDEAL_MAX:g} menit (tanpa syarat T_aktual)",
            "jumlah_tas": int(base_rule.sum()),
            "persen_tas_non_tergenang": float(base_rule.sum() / n_dry * 100) if n_dry else None,
            "sebaran_di_tas": _quantiles(di[base_rule]),
        },
        "sensitivitas_persentil": {
            "aturan": "T_ideal ≤ P25(T_ideal) dan DI_t ≥ P75(DI_t) pada grid non-Tergenang terjangkau",
            "p25_t_ideal": p25,
            "p75_di": p75,
            "jumlah_tas": int(is_tas_p.sum()),
            "persen_tas_non_tergenang": float(is_tas_p.sum() / n_dry * 100) if n_dry else None,
            "jumlah_tas_kedua_aturan": int((is_tas & is_tas_p).sum()),
            "jumlah_tas_hanya_aturan_utama": int((is_tas & ~is_tas_p).sum()),
            "jumlah_tas_hanya_persentil": int((~is_tas & is_tas_p).sum()),
            "sebaran_di_tas": _quantiles(di[is_tas_p]),
            "tas_per_kategori_tes_terdekat": {str(k): int(v) for k, v in
                                               pd.Series(kat[is_tas_p]).value_counts().sort_index().items()},
        },
        "jarak_euclid_min_m": TAS_MIN_EUCLID_M,
        "jumlah_t_aktual_lt_t_ideal": int((reach & (t_akt < t_ideal - 1e-9)).sum()),
        "jumlah_t_aktual_lt_euclid_tanpa_batas": int((reach & (t_akt < d_euc_raw / speed - 1e-9)).sum()),
    }
    return {"t_ideal": t_ideal, "t_aktual": t_akt, "detour_index": di, "t_euclid_raw": d_euc_raw / speed,
            "is_tas": is_tas.astype(int), "status": status, "status_persentil": status_p,
            "kategori_tes_terdekat": kat, "summary": summary}


def _quantiles(v: np.ndarray) -> dict:
    """Median, P25, P75, P90, dan n dari sebaran nilai (tanpa NaN)."""
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return {"n": 0, "median": None, "p25": None, "p75": None, "p90": None}
    q = np.percentile(v, [50, 25, 75, 90])
    return {"n": int(len(v)), "median": float(q[0]), "p25": float(q[1]), "p75": float(q[2]), "p90": float(q[3])}


# ══════════════════════════════════════════════════════════════════════════════
# 11. PIPELINE PER LEVEL (aksesibilitas + TAS) DAN KELUARAN
# ══════════════════════════════════════════════════════════════════════════════
def prepare_level(gdf_base, roads_raw, tes_raw, intensity: float, cfg: Cfg,
                  t_pen: Optional[float] = None, graph_pack: Optional[tuple] = None) -> dict:
    """Aksesibilitas + deteksi TAS satu level (tidak bergantung pada klasterisasi)."""
    acc = compute_level_accessibility(gdf_base, roads_raw, tes_raw, intensity, cfg,
                                      t_pen=t_pen, graph_pack=graph_pack)
    xy = np.column_stack([gdf_base["cx"].values, gdf_base["cy"].values])
    tas = detect_tas_detour(acc["df"], xy, acc["tes_v"], acc["graph"], acc["t_pen"], cfg,
                            tergenang=acc["df"]["tergenang"].values)
    return {**acc, "tas": tas, "level_key": level_from_intensity(intensity)["key"]}


def states_for_level(df: pd.DataFrame, pool_labels_level: np.ndarray, k: int) -> np.ndarray:
    """State per grid satu level: label tipologi (0..K−1) atau K = Tergenang."""
    st = np.full(len(df), k, dtype=int)
    st[df["tergenang"].values == 0] = pool_labels_level
    return st


def simulate_level(prep: dict, preprocessor: Preprocessor, centers: np.ndarray, gdf_base,
                   cfg: Cfg) -> dict:
    """Simulasi blokir jalan (dashboard, bukan hasil skripsi): fitur level disimulasikan ulang,
    ditransformasi dengan praproses data gabungan, lalu keanggotaan dihitung terhadap pusat
    klaster final yang TETAP (assign_to_centers) dengan W KNN-Gaussian level tersebut."""
    df = prep["df"]
    keep = df["tergenang"].values == 0
    X = preprocessor.transform(df.loc[keep])
    coords = np.column_stack([gdf_base["cx"].values[keep], gdf_base["cy"].values[keep]])
    W, _ = block_knn_weights(coords, np.zeros(int(keep.sum()), dtype=int), cfg.sdwfcm_knn)
    U = assign_to_centers(X, W, np.asarray(centers), cfg.sdwfcm_m, cfg.sdwfcm_alpha)
    k = len(centers)
    labels = np.full(len(df), -1, dtype=int)
    labels[keep] = U.argmax(axis=1)
    membership = np.full(len(df), np.nan)
    membership[keep] = U.max(axis=1)
    return {"labels": labels, "membership": membership, "states": np.where(keep, labels, k)}


def level_grid_frame(key: str, df: pd.DataFrame, tas: dict, cfg: Cfg) -> pd.DataFrame:
    """Atribut per grid dengan sufiks level yang tidak bergantung K (akses, Tergenang, TAS)."""
    out = pd.DataFrame({f"tergenang_{key}": df["tergenang"].values})
    for k in cfg.kategori_fac:
        out[f"waktu_{k}_{key}"] = np.round(df[f"waktu_tes_{k}"].values, 3)
    out[f"waktu_min_{key}"] = np.round(df["waktu_tes_min"].values, 3)
    out[f"opsi_{key}"] = df["jumlah_opsi_rute"].values
    out[f"t_ideal_{key}"] = np.round(tas["t_ideal"], 3)
    out[f"t_aktual_{key}"] = np.round(tas["t_aktual"], 3)
    out[f"di_{key}"] = np.round(tas["detour_index"], 4)
    out[f"tas_{key}"] = tas["is_tas"]
    out[f"tas_status_{key}"] = tas["status"]
    out[f"tas_status_persentil_{key}"] = tas["status_persentil"]
    out[f"tes_terdekat_{key}"] = tas["kategori_tes_terdekat"]
    return out


def model_grid_frame(key: str, k: int, labels: np.ndarray, membership: np.ndarray,
                     states: np.ndarray) -> pd.DataFrame:
    """Kolom model K per level: cl (−1 = Tergenang), mem (kosong untuk Tergenang), state (K = Tergenang)."""
    return pd.DataFrame({f"cl_{key}_k{k}": labels, f"mem_{key}_k{k}": np.round(membership, 4),
                         f"state_{key}_k{k}": states})


def records_from_grid(grid: pd.DataFrame, key: str, cfg: Cfg, k: int) -> List[dict]:
    """Array JSON ringan (tanpa geometri) untuk frontend, JOIN via id_grid, untuk model K."""
    cols = {
        "id_grid": "id_grid",
        "id_grid_asli": "id_grid_asli",
        f"cl_{key}_k{k}": "cluster_sdwfcm",
        f"mem_{key}_k{k}": "membership_max",
        f"tergenang_{key}": "tergenang",
        f"waktu_min_{key}": "waktu_tes_min",
        f"opsi_{key}": "jumlah_opsi_rute",
        f"t_ideal_{key}": "t_ideal",
        f"t_aktual_{key}": "t_aktual",
        f"di_{key}": "detour_index",
        f"tas_{key}": "titik_aman_semu",
        f"tas_status_{key}": "status_tas",
        f"tas_status_persentil_{key}": "status_tas_persentil",
        f"tes_terdekat_{key}": "tes_terdekat",
        f"akses_{key}": "kategori_akses",
        SKENARIO: "indeks_bahaya",
        "Road_Density_mean": "road_density",
    }
    for kk in cfg.kategori_fac:
        cols[f"waktu_{kk}_{key}"] = f"waktu_tes_{kk}"
    sub = grid[list(cols)].rename(columns=cols).copy()
    sub["is_isolated"] = (sub["jumlah_opsi_rute"] == 0).astype(int)
    for c in ["id_grid", "cluster_sdwfcm", "tergenang", "jumlah_opsi_rute",
              "titik_aman_semu", "status_tas", "status_tas_persentil", "kategori_akses", "is_isolated"]:
        sub[c] = sub[c].astype(int)
    sub["id_grid_asli"] = sub["id_grid_asli"].astype(str)
    sub["road_density"] = sub["road_density"].round(3)
    sub = sub.astype(object).where(pd.notna(sub), None)
    return sub.to_dict(orient="records")


def level_summary(key: str, prep: dict, cfg: Cfg) -> dict:
    """Ringkasan level yang tidak bergantung K (distribusi tipologi disimpan per model K)."""
    df = prep["df"]
    lv = LEVEL_BY_KEY[key]
    non = df["tergenang"].values == 0
    return {
        **lv,
        "n_grid": int(len(df)),
        "n_grid_tergenang": int((~non).sum()),
        "persen_grid_tergenang": float((~non).mean() * 100),
        "n_grid_non_tergenang": int(non.sum()),
        "n_roads_closed": prep["n_roads_closed"],
        "tes_valid": {kk: v["valid"] for kk, v in prep["tes_stats"].items()},
        "mean_waktu_min": float(df.loc[non, "waktu_tes_min"].mean()),
        "median_waktu_min": float(df.loc[non, "waktu_tes_min"].median()),
        "mean_waktu_min_semua_grid": float(df["waktu_tes_min"].mean()),
        "mean_waktu_min_tergenang": float(df.loc[~non, "waktu_tes_min"].mean()) if (~non).any() else None,
        "mean_waktu": {kk: float(df.loc[non, f"waktu_tes_{kk}"].mean()) for kk in cfg.kategori_fac},
        "n_isolated_non_tergenang": int(df.loc[non, "is_isolated"].sum()),
        "tas": prep["tas"]["summary"],
    }


def hazard_classes_affected(level: dict, gdf_base, roads_raw, cfg: Cfg, mask) -> dict:
    """Kelas bahaya banjir yang ditutup pada satu level: aturan (kelas_ditutup) dibandingkan
    dengan kelas grid yang benar-benar tergenang dan ruas yang benar-benar ditutup."""
    h = gdf_base[SKENARIO].fillna(0).astype(int).values
    grid_data = sorted(int(v) for v in np.unique(h[np.asarray(mask, bool)])) if np.any(mask) else []
    road_data = []
    if roads_raw is not None and SKENARIO in roads_raw.columns:
        rc = roads_raw[SKENARIO].fillna(0).astype(int).values
        closed = road_closed_mask(roads_raw, SKENARIO, level["intensity"], cfg)
        road_data = sorted(int(v) for v in np.unique(rc[closed])) if closed.any() else []
    rule = sorted(level["kelas_ditutup"])
    return {
        "kelas_ditutup_aturan": rule,
        "grid_tergenang_kelas_data": grid_data,
        "ruas_ditutup_kelas_data": road_data,
        "konsisten": grid_data == rule and road_data == rule,
        "tes_tidak_valid_kelas": f"kelas ≥ {cfg.tes_hazard_threshold} (semua level) + TES berkelas "
                                 f"< {cfg.tes_hazard_threshold} dalam radius 50 m grid tergenang",
    }


def level_diagnostics(prep: dict, gdf_base, roads_raw, cfg: Cfg) -> dict:
    """Diagnostik per level (tidak memengaruhi model)."""
    df = prep["df"]
    iso = df["jumlah_opsi_rute"].values == 0
    wet = df["tergenang"].values == 1
    tes_stats = prep["tes_stats"]
    return {
        "grid_tergenang": int(wet.sum()),
        "grid_terisolasi_non_tergenang": int((iso & ~wet).sum()),
        "grid_terisolasi_tergenang": int((iso & wet).sum()),
        "ruas_jalan_ditutup": int(prep["n_roads_closed"]),
        "tes_valid_per_kategori": {kat: int(v["valid"]) for kat, v in tes_stats.items()},
        "tes_total_per_kategori": {kat: int(v["total"]) for kat, v in tes_stats.items()},
        "tes_valid_total": int(sum(v["valid"] for v in tes_stats.values())),
        "kelas_bahaya": hazard_classes_affected(LEVEL_BY_KEY[prep["level_key"]],
                                                gdf_base, roads_raw, cfg, wet),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 12. STATISTIK DESKRIPTIF
# ══════════════════════════════════════════════════════════════════════════════
def describe_times(df: pd.DataFrame, cfg: Cfg) -> List[dict]:
    rows = []
    for col in [f"waktu_tes_{k}" for k in cfg.kategori_fac] + ["waktu_tes_min"]:
        v = df[col].astype(float).values
        rows.append({
            "variabel": col, "jumlah": int(len(v)), "mean": float(v.mean()),
            "std": float(v.std(ddof=1)), "min": float(v.min()),
            "q25": float(np.percentile(v, 25)), "median": float(np.median(v)),
            "q75": float(np.percentile(v, 75)), "max": float(v.max()),
        })
    return rows

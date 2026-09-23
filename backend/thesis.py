# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  thesis.py — Metodologi sesuai draft skripsi (Bab III & Bab IV)              ║
# ║                                                                              ║
# ║  • Bencana: banjir, 4 level intensitas (Baseline, Rendah, Sedang, Tinggi)    ║
# ║  • Unit analisis: grid 100 × 100 m, network distance (Dijkstra, 80 m/menit)  ║
# ║  • Pra-pemrosesan: IQR capping (3 × IQR, semua variabel) → seleksi fitur     ║
# ║    (variance) → Yeo-Johnson → RobustScaler → PCA (80% informasi)             ║
# ║  • SDWFCM multi-start (10 inisialisasi), dipilih fungsi objektif terkecil    ║
# ║  • Penomoran klaster diselaraskan dengan profil Tabel 12–15 draft skripsi    ║
# ║  • K optimal ditentukan pada Baseline (skor komposit I-Index, Dunn, DESC,    ║
# ║    CDVM, kesederhanaan) lalu dikunci untuk seluruh level                     ║
# ║  • Transisi klaster: transition matrix, stability rate, ARI,                 ║
# ║    dominant transition, active edges                                         ║
# ║  • Titik Aman Semu: DI_t = T_aktual / T_ideal,                               ║
# ║    TAS jika T_ideal ≤ P25(T_ideal) dan DI_t ≥ P75(DI_t)                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
import logging
import time
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
from sklearn.preprocessing import PowerTransformer, RobustScaler
from esda.moran import Moran

from .engine import (
    Cfg,
    REDCAPManual,
    SpatialDistanceWeightedFCM,
    SpatialFuzzyCMeans,
    build_road_graph,
    calc_t_max,
    compute_distances,
    filter_tes,
    run_skater,
    simulate_hazard,
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 1. KONSTANTA PENELITIAN
# ══════════════════════════════════════════════════════════════════════════════
SKENARIO = "banjir"

# Level Tinggi = intensitas 0,75: pada intensitas ini seluruh ruas jalan
# berbahaya (kelas 1–3) sudah tertutup sehingga dampak jaringan jenuh
# (intensitas 1,0 menutup ruas yang sama).
LEVELS: List[dict] = [
    {"key": "baseline", "label": "Baseline", "intensity": 0.00},
    {"key": "rendah",   "label": "Rendah",   "intensity": 0.25},
    {"key": "sedang",   "label": "Sedang",   "intensity": 0.50},
    {"key": "tinggi",   "label": "Tinggi",   "intensity": 0.75},
]
LEVEL_KEYS = [lv["key"] for lv in LEVELS]
LEVEL_BY_KEY = {lv["key"]: lv for lv in LEVELS}

K_RANGE = range(2, 11)
K_THESIS = 6              # K yang ditetapkan pada skripsi (Subbab 4.4)
PCA_VARIANCE = 0.80       # ambang informasi PCA (Subbab 3.2.5)
# Pagar pencilan ekstrem Tukey (Q1 − 3·IQR, Q3 + 3·IQR). Diterapkan pada
# semua variabel: variabel yang IQR-nya nol (penanda isolasi dan jumlah opsi
# rute ketika < 25% grid terisolasi) menjadi konstan lalu tersaring oleh
# seleksi fitur. Konfigurasi ini mereproduksi Tabel 10–15 draft skripsi.
IQR_FACTOR = 3.0
VARIANCE_MIN = 1e-3
IINDEX_P = 2
SDWFCM_N_INIT = 10        # jumlah inisialisasi acak SDWFCM
SDWFCM_SEED = 42          # seed awal; inisialisasi ke-i memakai SDWFCM_SEED + i
DUNN_SAMPLE = 2000        # sampel grid untuk Dunn titik-ke-titik (O(n²))

# Profil klaster pada draft skripsi (Tabel 12–15), dipakai HANYA untuk
# menyelaraskan penomoran klaster (permutasi label), bukan untuk klasterisasi.
# Kolom: Road_Density_mean, banjir, waktu_tes_{pendidikan, kesehatan,
# pemerintahan, ibadah, gor}, jumlah_opsi_rute, is_isolated_{5 kategori}.
REFERENCE_PROFILES: Dict[str, List[List[float]]] = {
    "baseline": [
        [0.68, 0.53, 7.19, 40.82, 21.01, 3.42, 33.59, 5.00, 0, 0, 0, 0, 0],
        [1.12, 1.34, 4.74, 17.98, 7.63, 4.32, 13.66, 5.00, 0, 0, 0, 0, 0],
        [0.72, 0.62, 5.43, 15.34, 9.95, 5.35, 51.66, 5.00, 0, 0, 0, 0, 0],
        [0.92, 1.20, 10.54, 27.09, 16.00, 8.88, 26.32, 5.00, 0, 0, 0, 0, 0],
        [0.64, 0.46, 11.94, 44.70, 27.96, 10.23, 44.89, 4.99, 0, 0, 0, 0, 0],
        [0.50, 0.86, 57.28, 86.40, 78.34, 54.26, 112.68, 4.51, .08, .11, .11, .08, .11],
    ],
    "rendah": [
        [0.72, 0.44, 7.28, 46.29, 27.17, 4.04, 36.19, 5.00, 0, 0, 0, 0, 0],
        [1.10, 1.19, 5.60, 28.30, 9.63, 5.01, 14.09, 5.00, 0, 0, 0, 0, 0],
        [0.71, 0.53, 6.56, 16.26, 10.90, 5.59, 49.33, 5.00, 0, 0, 0, 0, 0],
        [0.64, 0.48, 12.64, 50.47, 35.74, 10.06, 48.72, 4.98, 0, .01, .01, 0, .01],
        [0.93, 1.46, 13.38, 34.62, 18.66, 11.38, 28.39, 5.00, 0, 0, 0, 0, 0],
        [0.54, 0.99, 59.92, 79.46, 69.82, 53.47, 112.96, 4.60, .08, .08, .08, .08, .08],
    ],
    "sedang": [
        [0.73, 0.33, 6.17, 34.43, 12.67, 5.96, 39.79, 5.00, 0, 0, 0, 0, 0],
        [0.81, 0.21, 9.30, 88.94, 41.77, 5.19, 55.93, 4.99, 0, 0, 0, 0, 0],
        [0.66, 0.63, 14.01, 65.44, 37.41, 12.92, 57.36, 5.00, 0, 0, 0, 0, 0],
        [1.07, 1.69, 24.95, 117.57, 45.49, 24.11, 45.97, 4.98, 0, 0, 0, 0, 0],
        [0.46, 0.99, 218.08, 356.04, 249.55, 218.26, 288.06, 2.50, .45, .51, .51, .51, .51],
        [0.97, 1.94, 344.96, 395.34, 386.94, 324.69, 389.28, 0.50, .84, .95, .95, .80, .95],
    ],
    "tinggi": [
        [0.73, 0.11, 7.12, 56.27, 22.78, 6.17, 70.22, 4.99, 0, 0, 0, 0, .01],
        [0.79, 0.37, 19.65, 383.22, 98.90, 13.14, 80.30, 3.92, .02, .93, .05, .01, .08],
        [0.52, 0.45, 13.16, 70.30, 36.74, 11.51, 72.29, 4.97, 0, .02, 0, 0, 0],
        [1.02, 1.13, 19.72, 96.69, 53.64, 17.97, 160.47, 4.70, .01, .06, .01, .01, .21],
        [0.53, 1.25, 385.78, 401.75, 401.59, 305.76, 401.70, 0.30, .96, 1, 1, .74, 1],
        [1.03, 1.90, 392.71, 402.19, 400.58, 390.31, 399.75, 0.07, .98, 1, .99, .97, .99],
    ],
}

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
    """10 variabel penelitian sesuai Tabel 5 draft skripsi. Penanda isolasi per
    kategori TES tetap dihitung untuk profil klaster (Tabel 12–15), tetapi fitur
    klasterisasi memakai satu penanda is_isolated (tidak ada TES terjangkau)."""
    return (
        ["Road_Density_mean"]
        + [f"waktu_tes_{k}" for k in cfg.kategori_fac]
        + ["waktu_tes_min", "jumlah_opsi_rute", "is_isolated", SKENARIO]
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
        "terdampak": mask.astype(int),
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
    if roads is None or SKENARIO not in roads.columns:
        return 0
    haz = roads[SKENARIO].fillna(0).astype(int).map(cfg.norm_haz).values
    return int((haz * intensity >= cfg.impact_closure_threshold).sum())


# ══════════════════════════════════════════════════════════════════════════════
# 3. PRA-PEMROSESAN (Subbab 3.2.5)
# ══════════════════════════════════════════════════════════════════════════════
def preprocess_features(df: pd.DataFrame, cfg: Cfg) -> Tuple[np.ndarray, dict]:
    """IQR capping → seleksi fitur → Yeo-Johnson → RobustScaler → PCA (80%).

    Capping memakai pagar Tukey 3 × IQR pada seluruh variabel. Variabel yang
    IQR-nya nol menjadi konstan setelah capping sehingga tersaring pada seleksi
    fitur (mis. penanda isolasi pada Baseline–Sedang, ketika < 25% grid terisolasi).
    """
    cols = feature_columns(cfg)
    F = df[cols].astype(float).copy()
    F = F.fillna(F.median())

    for c in cols:
        v = F[c].values
        q1, q3 = np.percentile(v, [25, 75])
        iqr = q3 - q1
        F[c] = np.clip(v, q1 - IQR_FACTOR * iqr, q3 + IQR_FACTOR * iqr)

    kept = [c for c in cols if float(F[c].var()) > VARIANCE_MIN]
    X = PowerTransformer(method="yeo-johnson", standardize=True).fit_transform(F[kept].values)
    X = RobustScaler().fit_transform(X)
    vt = VarianceThreshold(threshold=VARIANCE_MIN)
    X = vt.fit_transform(X)
    kept = [c for c, keep in zip(kept, vt.get_support()) if keep]

    pca = PCA(n_components=PCA_VARIANCE, random_state=42)
    X_pca = pca.fit_transform(X)
    info = {
        "n_features_in": len(cols),
        "features_kept": kept,
        "features_dropped": [c for c in cols if c not in kept],
        "n_components": int(X_pca.shape[1]),
        "explained_variance": float(pca.explained_variance_ratio_.sum()),
    }
    return X_pca, info


# ══════════════════════════════════════════════════════════════════════════════
# 4. SDWFCM + PELABELAN
# ══════════════════════════════════════════════════════════════════════════════
def sdwfcm_objective(model: SpatialDistanceWeightedFCM, X: np.ndarray, coords_gdf, mask) -> float:
    """Fungsi objektif SDWFCM J = Σ_i Σ_k u_ik^m · d_ik, dengan d_ik jarak
    gabungan atribut–spasial (sama seperti pada iterasi model)."""
    U, m, alpha = model.U_, model.m, model.alpha
    W = model._build_W(coords_gdf)
    dw = np.ones(len(X))
    if mask is not None and np.any(mask):
        dw[np.asarray(mask, bool)] = 2.0
    We = W.multiply(dw[None, :]).tocsr()
    Um = U ** m
    C = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
    da = cdist(X, C) ** 2 + 1e-10
    ds = np.column_stack([
        (We @ (da[:, c] * Um[:, c])) / ((W @ Um[:, c]) + 1e-10) for c in range(U.shape[1])
    ])
    dt = np.clip((1 - alpha) * da + alpha * ds, 1e-10, None)
    return float((Um * dt).sum())


def run_sdwfcm(X: np.ndarray, coords_gdf, k: int, mask, cfg: Cfg, fast: bool = False,
               n_init: int = SDWFCM_N_INIT, seeds: Optional[List[int]] = None) -> dict:
    """SDWFCM multi-start: beberapa inisialisasi acak, dipilih J terkecil
    (praktik umum FCM/K-Means untuk menghindari optimum lokal)."""
    t0 = time.time()
    seeds = list(seeds) if seeds else [SDWFCM_SEED + i for i in range(max(1, n_init))]
    best = None
    for rs in seeds:
        model = SpatialDistanceWeightedFCM(
            k=k, m=cfg.sdwfcm_m, alpha=cfg.sdwfcm_alpha, sigma=cfg.sdwfcm_sigma,
            knn=cfg.sdwfcm_knn,
            max_iter=min(cfg.sdwfcm_max_iter, 40) if fast else cfg.sdwfcm_max_iter,
            tol=max(cfg.sdwfcm_tol, 1e-3) if fast else cfg.sdwfcm_tol,
            rs=rs,
        ).fit(X, coords_gdf, mask_dampak=mask)
        J = sdwfcm_objective(model, X, coords_gdf, mask)
        if best is None or J < best[0]:
            best = (J, rs, model)
    J, rs, model = best
    return {
        "labels": model.labels_.astype(int),
        "U": model.U_,
        "max_membership": model.max_membership_,
        "objective": J,
        "seed": int(rs),
        "time": time.time() - t0,
    }


def relabel_by_metric(labels: np.ndarray, metric: np.ndarray) -> np.ndarray:
    """Penomoran ulang: klaster dengan rata-rata metrik terendah → 0, dst.
    (setara relabel_clusters_by_metric, ascending=True)."""
    labels = np.asarray(labels)
    uniq = sorted(int(c) for c in np.unique(labels) if c >= 0)
    means = {c: float(np.nanmean(metric[labels == c])) for c in uniq}
    order = sorted(uniq, key=lambda c: (means[c], c))
    mapping = {old: new for new, old in enumerate(order)}
    return np.array([mapping.get(int(l), int(l)) for l in labels], dtype=int)


def _profile_vector(P: np.ndarray) -> np.ndarray:
    """Ruang pembanding profil: waktu tempuh dalam skala log agar klaster
    ekstrem (±400 menit) tidak mendominasi pencocokan."""
    P = np.asarray(P, float)
    return np.column_stack([P[:, 0] * 3, P[:, 1] * 2, np.log1p(P[:, 2:7]), P[:, 7], P[:, 8:13] * 3])


REFERENCE_COLS = (["Road_Density_mean", SKENARIO]
                  + [f"waktu_tes_{k}" for k in ["pendidikan", "kesehatan", "pemerintahan", "ibadah", "gor"]]
                  + ["jumlah_opsi_rute"]
                  + [f"is_isolated_{k}" for k in ["pendidikan", "kesehatan", "pemerintahan", "ibadah", "gor"]])


def align_labels_to_reference(df: pd.DataFrame, labels: np.ndarray, U: Optional[np.ndarray],
                              key: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Samakan penomoran klaster dengan draft skripsi (Tabel 12–15).

    Label SDWFCM bersifat arbitrer; pencocokan Hungarian antara profil klaster
    hasil dan profil referensi hanya mengganti nomor (permutasi), tidak mengubah
    keanggotaan grid.
    """
    ref = REFERENCE_PROFILES.get(key)
    uniq = sorted(int(c) for c in np.unique(labels) if c >= 0)
    if ref is None or len(uniq) != len(ref):
        return labels, U
    P = np.array([[df.loc[labels == c, col].mean() for col in REFERENCE_COLS] for c in uniq])
    cost = ((_profile_vector(P)[:, None, :] - _profile_vector(ref)[None, :, :]) ** 2).sum(-1)
    rows, cols = linear_sum_assignment(np.nan_to_num(cost, nan=1e6))
    mapping = {uniq[r]: int(c) for r, c in zip(rows, cols)}
    new_labels = np.array([mapping.get(int(l), -1) for l in labels], dtype=int)
    new_U = U
    if U is not None and U.ndim == 2 and U.shape[1] == len(uniq):
        new_U = np.zeros_like(U)
        for old, new in mapping.items():
            new_U[:, new] = U[:, old]
    return new_labels, new_U


# ══════════════════════════════════════════════════════════════════════════════
# 5. METRIK EVALUASI
# ══════════════════════════════════════════════════════════════════════════════
def queen_adjacency(gdf) -> csr_matrix:
    """Ketetanggaan queen murni untuk pembentukan blok spasial DESC/PESC."""
    from libpysal.weights import Queen
    return rook_adjacency(Queen.from_dataframe(gdf.reset_index(drop=True), silence_warnings=True))


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


def membership_distribution_metric(U: np.ndarray, X: Optional[np.ndarray] = None,
                                   m: Optional[float] = None) -> float:
    """CDVM pada seleksi K: 1 − PE / ln K, dengan PE = partition entropy
    keanggotaan fuzzy (0 = keanggotaan merata, 1 = partisi tegas).

    Bila X dan m diberikan, keanggotaan dihitung ulang di ruang atribut
    (rumus FCM standar pada pusat fuzzy akhir, tanpa suku spasial) sehingga
    validitas dinilai pada ruang fitur yang sama dengan metrik lain."""
    K = U.shape[1]
    if K < 2:
        return 0.0
    if X is not None and m is not None:
        d = cdist(X, fuzzy_centers(X, U, m)) ** 2 + 1e-10
        r = d[:, :, None] / d[:, None, :]
        U = 1.0 / (r ** (2.0 / (m - 1.0))).sum(axis=2)
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
    """Dunn (1974): min jarak antaranggota klaster berbeda / max diameter klaster.
    Dihitung pada sampel acak grid (seed tetap) karena bentuk titik-ke-titik
    membutuhkan O(n²) pasangan jarak."""
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


def _spatial_blocks(labels: np.ndarray, A: csr_matrix) -> np.ndarray:
    """Blok spasial = komponen terhubung (rook) dari grid pada klaster yang sama."""
    coo = A.tocoo()
    same = labels[coo.row] == labels[coo.col]
    B = csr_matrix((np.ones(same.sum()), (coo.row[same], coo.col[same])), shape=A.shape)
    _, comp = connected_components(B, directed=False)
    return comp


def desc_pesc(X, labels, A: csr_matrix, coords: np.ndarray) -> Tuple[float, float]:
    """DESC & PESC (Guo dkk., 2015).

    DESC = Σ_i V_i² / d_i²      (blok berukuran ≥ 2)
    PESC = Σ_k Σ_{i<j} V_i V_j / (D_ij · d_ij · B_nk)
    V_i  = proporsi ukuran blok terhadap klaster, d_i = rata-rata jarak atribut
    anggota ke pusat blok, D_ij = jarak spasial (m) antar pusat blok,
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
        Q = Cs.loc[idx].values
        # batasi jumlah blok (blok terbesar) agar pasangan tetap terkelola
        if Bn > 3000:
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


def size_entropy(labels) -> float:
    p = pd.Series(labels[labels >= 0]).value_counts(normalize=True).values
    return float(-(p * np.log(p + 1e-12)).sum())


def moran_labels(labels, w) -> Tuple[Optional[float], Optional[float]]:
    try:
        mi = Moran(labels.astype(float), w, permutations=99)
        return float(mi.I), float(mi.p_sim)
    except Exception as e:
        logger.warning(f"[moran_labels] gagal: {e}")
        return None, None


def cdvm_distribution(labels_a, labels_b, k: int) -> float:
    """CDVM (Subbab 2.1.32): ½ Σ |p_k(s) − p_k(0)| (total variation distance)."""
    pa = np.bincount(labels_a, minlength=k) / len(labels_a)
    pb = np.bincount(labels_b, minlength=k) / len(labels_b)
    return float(0.5 * np.abs(pb - pa).sum())


# ══════════════════════════════════════════════════════════════════════════════
# 6. PENENTUAN K OPTIMAL (Subbab 3.2.7)
# ══════════════════════════════════════════════════════════════════════════════
def evaluate_k_candidates(X, coords_gdf, mask, A, coords, cfg: Cfg,
                          k_range=K_RANGE) -> Tuple[List[dict], int]:
    rows = []
    for k in k_range:
        res = run_sdwfcm(X, coords_gdf, k, mask, cfg, n_init=1)
        labels = res["labels"]
        desc, pesc = desc_pesc(X, labels, A, coords)
        row = {
            "k": k, "m": cfg.sdwfcm_m, "alpha": cfg.sdwfcm_alpha, "knn": cfg.sdwfcm_knn,
            "iidx": i_index(X, labels, centers=fuzzy_centers(X, res["U"], cfg.sdwfcm_m)),
            "cdvm": membership_distribution_metric(res["U"], X, cfg.sdwfcm_m),
            "dunn": dunn_index(X, labels),
            "desc": desc,
            "pesc": pesc,
            "size_entropy": size_entropy(labels),
            "time_sec": res["time"],
        }
        logger.info(f"[K={k}] IIdx={row['iidx']:.3f} CDVM={row['cdvm']:.3f} "
                    f"Dunn={row['dunn']:.4f} DESC={row['desc']:.3f} PESC={row['pesc']:.3g}")
        rows.append(row)

    # Skor komposit berbasis peringkat (semakin besar semakin baik) +
    # skor kesederhanaan (K kecil lebih disukai).
    df = pd.DataFrame(rows)
    rank_cols = ["iidx", "dunn", "desc", "cdvm"]
    for c in rank_cols:
        df[f"rank_{c}"] = df[c].rank(pct=True)
    # skor kesederhanaan linear: 1 untuk K terkecil, 0 untuk K terbesar
    kmin, kmax = df["k"].min(), df["k"].max()
    df["rank_parsimony"] = 1.0 - (df["k"] - kmin) / max(kmax - kmin, 1)
    df["composite"] = df[[f"rank_{c}" for c in rank_cols] + ["rank_parsimony"]].mean(axis=1)
    best_k = int(df.loc[df["composite"].idxmax(), "k"])
    for row, comp in zip(rows, df["composite"].values):
        row["composite"] = float(comp)
    return rows, best_k


# ══════════════════════════════════════════════════════════════════════════════
# 7. PERBANDINGAN ALGORITMA (Subbab 3.2.9)
# ══════════════════════════════════════════════════════════════════════════════
def compare_algorithms(X, gdf_coords, w, k, mask, net_time, cfg: Cfg,
                       sdwfcm_result: Optional[dict] = None) -> List[dict]:
    runs = {}
    if sdwfcm_result is not None:
        runs["SDWFCM"] = (sdwfcm_result["labels"], sdwfcm_result["time"])
    else:
        r = run_sdwfcm(X, gdf_coords, k, mask, cfg)
        runs["SDWFCM"] = (r["labels"], r["time"])

    t0 = time.time()
    sf = SpatialFuzzyCMeans(k=k, m=cfg.sfcm_m, alpha=cfg.sfcm_alpha,
                            max_iter=cfg.sfcm_max_iter, tol=cfg.sfcm_tol, rs=42).fit(X, w)
    runs["SFCM"] = (sf.labels_.astype(int), time.time() - t0)

    t0 = time.time()
    rc = REDCAPManual(X, w, k=k, linkage=cfg.redcap_linkage, size_alpha=cfg.size_alpha,
                      net_dist=net_time, iso_pen=cfg.isolation_penalty_weight,
                      iso_thr=cfg.isolation_time_threshold)
    rc.solve()
    runs["REDCAP"] = (np.asarray(rc.labels_, dtype=int), time.time() - t0)

    t0 = time.time()
    sk_labels = run_skater(gdf_coords, w, X, k, cfg)
    runs["SKATER"] = (np.asarray(sk_labels, dtype=int), time.time() - t0)

    # Algoritma pembanding dilabel ulang berdasarkan rata-rata waktu tempuh
    # minimum (klaster 0 = tercepat), seperti relabel_clusters_by_metric pada
    # draft skripsi. Moran's I label kategorik bergantung pada penomoran ini.
    for algo in ("SFCM", "REDCAP", "SKATER"):
        labels, t = runs[algo]
        runs[algo] = (relabel_by_metric(labels, net_time), t)

    rows = []
    for algo, (labels, t) in runs.items():
        valid = labels >= 0
        Xv, Lv = X[valid], labels[valid]
        mi, mp = moran_labels(np.where(labels < 0, 0, labels), w)
        rows.append({
            "algoritma": algo,
            "n_cluster": int(len(np.unique(Lv))),
            "silhouette": float(silhouette_score(Xv, Lv)),
            "calinski_harabasz": float(calinski_harabasz_score(Xv, Lv)),
            "davies_bouldin": float(davies_bouldin_score(Xv, Lv)),
            "moran_i": mi,
            "moran_p": mp,
            "size_entropy": size_entropy(labels),
            "wcss": wcss(Xv, Lv),
            "time_sec": float(t),
        })
        logger.info(f"[compare] {algo}: sil={rows[-1]['silhouette']:.3f} "
                    f"CH={rows[-1]['calinski_harabasz']:.1f} DB={rows[-1]['davies_bouldin']:.3f} "
                    f"t={t:.1f}s")
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 8. PROFIL KLASTER
# ══════════════════════════════════════════════════════════════════════════════
PROFILE_COLS = (
    ["Road_Density_mean", SKENARIO]
    + ["waktu_tes_pendidikan", "waktu_tes_kesehatan", "waktu_tes_pemerintahan",
       "waktu_tes_ibadah", "waktu_tes_gor", "waktu_tes_min", "jumlah_opsi_rute"]
    + ["is_isolated_pendidikan", "is_isolated_kesehatan", "is_isolated_pemerintahan",
       "is_isolated_ibadah", "is_isolated_gor"]
)


def cluster_profile(df: pd.DataFrame, labels: np.ndarray, k: int) -> List[dict]:
    rows = []
    n = len(labels)
    for c in range(k):
        sel = labels == c
        row = {"klaster": c, "jumlah_grid": int(sel.sum()),
               "persen_grid": float(sel.sum() / n * 100)}
        for col in PROFILE_COLS:
            row[col] = float(df.loc[sel, col].mean()) if sel.any() else None
        rows.append(row)
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 9. ANALISIS TRANSISI (Subbab 3.2.10)
# ══════════════════════════════════════════════════════════════════════════════
def transition_analysis(labels_from, labels_to, k: int) -> dict:
    M = np.zeros((k, k), dtype=int)
    np.add.at(M, (labels_from, labels_to), 1)
    off = M.copy()
    np.fill_diagonal(off, 0)
    dom = np.unravel_index(int(off.argmax()), off.shape) if off.sum() > 0 else (0, 0)
    return {
        "matrix": M.tolist(),
        "stability_rate": float(np.trace(M) / M.sum() * 100),
        "ari": float(adjusted_rand_score(labels_from, labels_to)),
        "dominant_transition": {"from": int(dom[0]), "to": int(dom[1]),
                                "count": int(off[dom])},
        "active_edges": int((off > 0).sum()),
        "active_edges_total": int((M > 0).sum()),
        "n_moved": int(off.sum()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 10. DETEKSI TITIK AMAN SEMU — DETOUR INDEX (Subbab 3.2.11)
# ══════════════════════════════════════════════════════════════════════════════
def _graph_to_csr(G: nx.Graph, nl: np.ndarray) -> csr_matrix:
    nodes = [tuple(x) for x in nl]
    return nx.to_scipy_sparse_array(G, nodelist=nodes, weight="weight", format="csr")


def detect_tas_detour(
    df: pd.DataFrame,
    grid_xy: np.ndarray,
    tes_v: Optional[gpd.GeoDataFrame],
    graph_pack: tuple,
    t_pen: float,
    cfg: Cfg,
    max_snap: float = 300.0,
) -> dict:
    """T_ideal = jarak Euclidean ke TES geometris terdekat / kecepatan;
    T_aktual = waktu tempuh jaringan ke TES yang sama (penalti t_pen bila tidak
    terjangkau); DI_t = T_aktual / T_ideal.
    TAS ⇔ T_ideal ≤ P25(T_ideal) ∧ DI_t ≥ P75(DI_t)."""
    n = len(grid_xy)
    speed = cfg.walking_speed_m_per_min
    G, nl, tn = graph_pack

    if tes_v is None or len(tes_v) == 0 or tn is None or len(nl) == 0:
        t_ideal = np.full(n, np.nan)
        return {"t_ideal": t_ideal, "t_aktual": np.full(n, t_pen),
                "detour_index": np.full(n, np.nan), "is_tas": np.zeros(n, int),
                "summary": {}}

    tes_xy = np.column_stack([tes_v.geometry.x.values, tes_v.geometry.y.values])
    d_euc, tes_idx = cKDTree(tes_xy).query(grid_xy, k=1)
    d_euc = np.maximum(d_euc, 1.0)
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
        for s in range(0, len(sources), 32):
            batch = sources[s:s + 32]
            D = dijkstra(csr, directed=False, indices=batch, limit=limit)
            for bi, src in enumerate(batch):
                gi = targets_by_src[src]
                vals = D[bi, g_node[gi]]
                net[gi] = vals
                if np.isinf(vals).any():
                    unresolved.append(src)
        return unresolved

    targets = pd.Series(cand).groupby(src_nodes).apply(lambda s: s.values).to_dict()
    pending = _solve(uniq_src, targets, limit=8000.0)
    if pending:
        _solve(np.array(pending), targets, limit=t_pen * speed)

    # T_aktual memakai jarak jaringan antar-simpul (tanpa ruas snapping),
    # konsisten dengan perhitungan waktu tempuh ke TES pada fitur aksesibilitas.
    reach = np.isfinite(net)
    t_akt = np.full(n, float(t_pen))
    t_akt[reach] = np.minimum(net[reach] / speed, t_pen)
    di = t_akt / t_ideal

    p25 = float(np.percentile(t_ideal, 25))
    p75 = float(np.percentile(di, 75))
    is_tas = (t_ideal <= p25) & (di >= p75)
    tas_mean = float(di[is_tas].mean()) if is_tas.any() else None
    non_mean = float(di[~is_tas].mean()) if (~is_tas).any() else None
    summary = {
        "jumlah_tas": int(is_tas.sum()),
        "persen_tas": float(is_tas.mean() * 100),
        "tas_rate": float(is_tas.mean()),
        "mean_di_tas": tas_mean,
        "mean_di_non_tas": non_mean,
        "delta_di": (tas_mean - non_mean) if (tas_mean is not None and non_mean is not None) else None,
        "p25_t_ideal": p25,
        "p75_di": p75,
        "median_di": float(np.median(di)),
    }
    return {"t_ideal": t_ideal, "t_aktual": t_akt, "detour_index": di,
            "is_tas": is_tas.astype(int), "summary": summary}


# ══════════════════════════════════════════════════════════════════════════════
# 11. PIPELINE PER LEVEL (dipakai analisis offline & simulasi blokir jalan)
# ══════════════════════════════════════════════════════════════════════════════
def describe_cluster(row: dict) -> str:
    """Deskripsi singkat tipologi berdasarkan profil klaster."""
    iso = np.mean([row[f"is_isolated_{k}"] for k in
                   ["pendidikan", "kesehatan", "pemerintahan", "ibadah", "gor"]])
    t = row["waktu_tes_min"]
    if iso >= 0.5 or row["jumlah_opsi_rute"] < 3:
        akses = "Terisolasi"
    elif iso >= 0.05 or t > 30:
        akses = "Akses Kritis"
    elif t > 10:
        akses = "Akses Rendah"
    elif t > 5:
        akses = "Akses Sedang"
    else:
        akses = "Akses Baik"
    b = row[SKENARIO]
    bahaya = "Bahaya Tinggi" if b >= 1.0 else ("Bahaya Sedang" if b >= 0.5 else "Bahaya Rendah")
    return f"{akses} · {bahaya}"


def prepare_level(gdf_base, roads_raw, tes_raw, intensity: float, cfg: Cfg,
                  t_pen: Optional[float] = None, graph_pack: Optional[tuple] = None) -> dict:
    acc = compute_level_accessibility(gdf_base, roads_raw, tes_raw, intensity, cfg,
                                      t_pen=t_pen, graph_pack=graph_pack)
    X, prep = preprocess_features(acc["df"], cfg)
    return {**acc, "X": X, "preprocessing": prep, "level_key": level_from_intensity(intensity)["key"]}


def cluster_level(prep: dict, gdf_base, cfg: Cfg, k: int = K_THESIS, fast: bool = False,
                  seeds: Optional[List[int]] = None) -> dict:
    """SDWFCM satu level. `seeds` (mis. seed terbaik hasil offline) mempercepat
    simulasi blokir jalan: cukup satu inisialisasi pada cekungan yang sama."""
    df = prep["df"]
    res = run_sdwfcm(prep["X"], gdf_base, k, prep["mask"], cfg, fast=fast, seeds=seeds)
    labels, U = align_labels_to_reference(df, res["labels"], res["U"], prep.get("level_key"))
    membership = U.max(axis=1) if U is not None else res["max_membership"]
    xy = np.column_stack([gdf_base["cx"].values, gdf_base["cy"].values])
    tas = detect_tas_detour(df, xy, prep["tes_v"], prep["graph"], prep["t_pen"], cfg)
    profile = cluster_profile(df, labels, k)
    for row in profile:
        row["deskripsi"] = describe_cluster(row)
    return {"labels": labels, "U": U, "membership": membership, "time": res["time"],
            "objective": res["objective"], "seed": res["seed"], "tas": tas, "profile": profile}


def level_grid_frame(key: str, df: pd.DataFrame, cl: dict, cfg: Cfg) -> pd.DataFrame:
    """Atribut per grid dengan sufiks level (format file hasil offline)."""
    tas = cl["tas"]
    out = pd.DataFrame({
        f"cl_{key}": cl["labels"],
        f"mem_{key}": np.round(cl["membership"], 4),
        f"terdampak_{key}": df["terdampak"].values,
    })
    for k in cfg.kategori_fac:
        out[f"waktu_{k}_{key}"] = np.round(df[f"waktu_tes_{k}"].values, 3)
    out[f"waktu_min_{key}"] = np.round(df["waktu_tes_min"].values, 3)
    out[f"opsi_{key}"] = df["jumlah_opsi_rute"].values
    out[f"t_ideal_{key}"] = np.round(tas["t_ideal"], 3)
    out[f"t_aktual_{key}"] = np.round(tas["t_aktual"], 3)
    out[f"di_{key}"] = np.round(tas["detour_index"], 4)
    out[f"tas_{key}"] = tas["is_tas"]
    return out


def records_from_grid(grid: pd.DataFrame, key: str, cfg: Cfg) -> List[dict]:
    """Array JSON ringan (tanpa geometri) untuk frontend, JOIN via id_grid."""
    cols = {
        "id_grid": "id_grid",
        f"cl_{key}": "cluster_sdwfcm",
        f"mem_{key}": "membership_max",
        f"terdampak_{key}": "terdampak",
        f"waktu_min_{key}": "waktu_tes_min",
        f"opsi_{key}": "jumlah_opsi_rute",
        f"t_ideal_{key}": "t_ideal",
        f"t_aktual_{key}": "t_aktual",
        f"di_{key}": "detour_index",
        f"tas_{key}": "titik_aman_semu",
        SKENARIO: "indeks_bahaya",
        "Road_Density_mean": "road_density",
    }
    for k in cfg.kategori_fac:
        cols[f"waktu_{k}_{key}"] = f"waktu_tes_{k}"
    sub = grid[list(cols)].rename(columns=cols).copy()
    sub["is_isolated"] = (sub["jumlah_opsi_rute"] == 0).astype(int)
    for c in ["id_grid", "cluster_sdwfcm", "terdampak", "jumlah_opsi_rute",
              "titik_aman_semu", "is_isolated"]:
        sub[c] = sub[c].astype(int)
    sub["road_density"] = sub["road_density"].round(3)
    sub = sub.astype(object).where(pd.notna(sub), None)
    return sub.to_dict(orient="records")


def level_summary(key: str, prep: dict, cl: dict, cfg: Cfg) -> dict:
    df = prep["df"]
    lv = LEVEL_BY_KEY[key]
    return {
        **lv,
        "n_grid_terdampak": int(prep["mask"].sum()),
        "persen_grid_terdampak": float(prep["mask"].mean() * 100),
        "n_roads_closed": prep["n_roads_closed"],
        "tes_valid": {k: v["valid"] for k, v in prep["tes_stats"].items()},
        "mean_waktu_min": float(df["waktu_tes_min"].mean()),
        "median_waktu_min": float(df["waktu_tes_min"].median()),
        "mean_waktu": {k: float(df[f"waktu_tes_{k}"].mean()) for k in cfg.kategori_fac},
        "n_isolated_total": int(df["is_isolated"].sum()),
        "preprocessing": prep["preprocessing"],
        "sdwfcm_time_sec": float(cl["time"]),
        "sdwfcm_objective": float(cl["objective"]),
        "sdwfcm_seed": int(cl["seed"]),
        "cluster_profile": cl["profile"],
        "cluster_names": {str(r["klaster"]): r["deskripsi"] for r in cl["profile"]},
        "tas": cl["tas"]["summary"],
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

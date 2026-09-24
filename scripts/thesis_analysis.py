"""Analisis offline penelitian (menghasilkan seluruh angka Bab IV).

Menghasilkan:
  data/thesis_results.json           — ringkasan seluruh tabel/metrik Bab IV
  data/thesis_grid_results.csv.gz    — atribut per grid untuk setiap level
  data/thesis_pooled_results.csv.gz  — data gabungan (id_grid, id_grid_asli, level, fitur, PCA,
                                       klaster, keanggotaan)

Jalankan:  python -m scripts.thesis_analysis --force
           tambahkan --skip-comparison untuk melewati perbandingan algoritma.
"""
import os

# Determinisme: satu thread BLAS/OpenMP (harus di-set sebelum numpy dimuat).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import hashlib
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine import Cfg, build_weights, load_data, load_road_network
from backend import thesis as T

logger = logging.getLogger("ThesisAnalysis")

RESULTS_FILE = "thesis_results.json"
GRID_FILE = "thesis_grid_results.csv.gz"
POOLED_FILE = "thesis_pooled_results.csv.gz"     # data gabungan (grid × level non-Tergenang)
RESULT_FILES = (RESULTS_FILE, GRID_FILE, POOLED_FILE)
LOCK_DIR = "locked"
LOCK_FILE = "LOCK.json"


def is_locked(data_dir) -> bool:
    return (Path(data_dir) / LOCK_DIR / LOCK_FILE).exists()


def restore_locked(data_dir) -> bool:
    """Salin hasil terkunci ke data/ bila berkas kerja hilang. Mengembalikan True bila berhasil."""
    import shutil
    lock_dir = Path(data_dir) / LOCK_DIR
    if not (lock_dir / LOCK_FILE).exists():
        return False
    for f in RESULT_FILES:
        if (lock_dir / f).exists():
            shutil.copy2(lock_dir / f, Path(data_dir) / f)
    return all((Path(data_dir) / f).exists() for f in (RESULTS_FILE, GRID_FILE))


TIME_KEYS = {"elapsed_sec", "time_sec", "sdwfcm_time_sec", "time_per_init_sec",   # dibuang sebelum hashing
             "waktu_komputasi", "waktu_inisialisasi_sec", "waktu_subsampel_sec", "waktu_metrik_sec",
             "git"}                                           # identitas commit (bukan hasil)


def _strip_time(obj):
    if isinstance(obj, dict):
        return {k: _strip_time(v) for k, v in obj.items() if k not in TIME_KEYS}
    if isinstance(obj, list):
        return [_strip_time(v) for v in obj]
    return obj


def results_fingerprint(path) -> str:
    """SHA-256 thesis_results.json setelah field waktu dibuang (JSON kanonik, kunci terurut)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    canon = json.dumps(_strip_time(data), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


UNROUNDED_KEYS = {"pesc"}   # nilai sangat kecil: disimpan tanpa pembulatan


def clean_json(obj, key=None):
    """Konversi ke tipe JSON; float dibulatkan 6 desimal kecuali kunci di UNROUNDED_KEYS."""
    if isinstance(obj, dict):
        return {str(k): clean_json(v, str(k)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v, key) for v in obj]
    if isinstance(obj, np.ndarray):
        return clean_json(obj.tolist(), key)
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        if not np.isfinite(v):
            return None
        return v if key in UNROUNDED_KEYS else round(v, 6)
    return obj


CODE_PATHS = ["backend", "scripts", "tests", "requirements.txt", ".python-version"]


def git_info(root=PROJECT_ROOT) -> dict:
    """Commit, branch, dan status perubahan kode (hanya CODE_PATHS) saat analisis dijalankan."""
    import subprocess
    def _git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                                  check=True).stdout.strip()
        except Exception:
            return None
    dirty = _git("status", "--porcelain", "--", *CODE_PATHS)
    return {"commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "kode_berubah_belum_commit": bool(dirty) if dirty is not None else None}


def run_thesis_analysis(data_dir=None, skip_comparison: bool = False, force: bool = False,
                        subsample_b: int = T.SUBSAMPLE_B) -> dict:
    t_start = time.time()
    data_dir = data_dir or os.environ.get("SDWFCM_DATA_DIR", str(PROJECT_ROOT / "data"))
    if is_locked(data_dir) and not force:
        restore_locked(data_dir)
        logger.warning("Hasil analisis TERKUNCI (data/locked/LOCK.json) — analisis tidak dijalankan. "
                       "Gunakan --force untuk menimpa.")
        return json.loads((Path(data_dir) / RESULTS_FILE).read_text(encoding="utf-8"))
    cfg = Cfg(base_dir=data_dir)
    timing = {}

    def _tick(name, t0):
        timing[name] = time.time() - t0
        logger.info(f"[waktu] {name}: {timing[name]:.1f} s")
        return time.time()

    t = time.time()
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    w = build_weights(gdf)                 # rook (+ perbaikan pulau/komponen) — Moran's I, SFCM, REDCAP
    A_rook = T.rook_adjacency(w)
    t = _tick("muat_data", t)

    results = {
        "meta": {
            "git": git_info(),
            "versi_desain": "v3 (kelas bahaya dari raster InaRisk, TAS aturan absolut, keluaran K = 2 dan 3)",
            "sumber_kelas_bahaya": "data/Kulonprogo_Banjir.tif (grid mayoritas, ruas maksimum, TES titik)",
            "skenario": T.SKENARIO,
            "levels": T.LEVELS,
            "walking_speed_m_per_min": cfg.walking_speed_m_per_min,
            "sdwfcm": {"m": cfg.sdwfcm_m, "alpha": cfg.sdwfcm_alpha, "knn": cfg.sdwfcm_knn,
                       "impact_weight": cfg.sdwfcm_impact_weight},
            "sfcm": {"m": cfg.sdwfcm_m, "alpha": cfg.sfcm_alpha},
            "pca_variance": T.PCA_VARIANCE,
            "iqr_factor": T.IQR_FACTOR,
            "capped_columns": T.CAPPED_COLUMNS,
            "fitur_klasterisasi": T.feature_columns(cfg),
            "sdwfcm_n_init": T.SDWFCM_N_INIT,
            "feature_labels": T.FEATURE_LABELS,
            "tas_status": T.TAS_STATUS,
            "tas_aturan_utama": {"di_min": T.TAS_DI_ABSOLUTE, "t_ideal_maks_menit": T.TAS_T_IDEAL_MAX,
                                 "jarak_min_m": T.TAS_MIN_EUCLID_M},
            "label_interpretasi": {"terisolasi_proporsi_penalti_lebih_dari": T.LABEL_TERISOLASI_MIN,
                                   "akses_baik_median_maks": T.LABEL_BAIK_MAX,
                                   "akses_sedang_median_maks": T.LABEL_SEDANG_MAX},
        },
        "data_summary": {
            "n_grid": int(len(gdf)),
            "n_road_segments": int(len(roads)) if roads is not None else 0,
            "crs": cfg.target_crs,
            "tes_counts": {k: int(len(v)) for k, v in tes.items()},
        },
        "levels": {},
    }

    # ── 1. Aksesibilitas + TAS per level ─────────────────────────────────────
    t_pen, preps = None, {}
    for lv in T.LEVELS:
        logger.info(f"===== AKSESIBILITAS {lv['label_lengkap'].upper()} =====")
        prep = T.prepare_level(gdf, roads, tes, lv["intensity"], cfg, t_pen=t_pen)
        t_pen = prep["t_pen"]
        prep.pop("graph")                  # graf tidak diperlukan lagi (hemat memori)
        preps[lv["key"]] = prep
    results["t_pen"] = t_pen
    results["baseline_time_stats"] = T.describe_times(preps["baseline"]["df"], cfg)
    t = _tick("aksesibilitas_dan_tas", t)

    # ── 2. Data gabungan, praproses, W blok-diagonal ─────────────────────────
    pool = T.build_pooled({k: p["df"] for k, p in preps.items()}, gdf)
    pre = T.Preprocessor.fit(pool, cfg)
    X = pre.transform(pool)
    coords = pool[["cx", "cy"]].values
    groups = pool["level"].values
    W, sigmas = T.block_knn_weights(coords, groups, cfg.sdwfcm_knn)
    grid_idx = pool["id_grid"].values.astype(int)
    A_pool = T.block_adjacency(A_rook, grid_idx, groups)
    results["preprocessing"] = pre.to_dict()
    results["data_gabungan"] = {
        "n_baris": int(len(pool)),
        "n_baris_per_level": {k: int((groups == k).sum()) for k in T.LEVEL_KEYS},
        "sigma_per_level": sigmas,
        "knn": cfg.sdwfcm_knn,
    }
    t = _tick("data_gabungan_praproses_W", t)

    # ── 3. Pemilihan K (stabilitas, dihitung ulang pada data v3) ─────────────
    k_rows, k_summary, solutions = T.evaluate_k_stability(X, W, pool, A_pool, cfg, B=subsample_b)
    results["k_selection"] = {"candidates": k_rows, **k_summary}
    results["k_terpilih_aturan"] = k_summary["k_terpilih"]
    results["k_keluaran"] = list(T.K_OUTPUT)
    t = _tick("pemilihan_k", t)

    # ── 4. Keluaran tingkat grid yang tidak bergantung K ─────────────────────
    grid_parts = [pd.DataFrame({
        "id_grid": gdf["id_grid"].values,
        "id_grid_asli": gdf["id_grid_asli"].values,
        "Road_Density_mean": gdf["Road_Density_mean"].values,
        T.SKENARIO: gdf[T.SKENARIO].values,
        f"{T.SKENARIO}_atribut_lama": gdf[f"{T.SKENARIO}_atribut_lama"].values,
    })]
    for lv in T.LEVELS:
        key = lv["key"]
        summary = T.level_summary(key, preps[key], cfg)
        summary["diagnostik"] = T.level_diagnostics(preps[key], gdf, roads, cfg)
        results["levels"][key] = summary
        grid_parts.append(T.level_grid_frame(key, preps[key]["df"], preps[key]["tas"], cfg))
    pooled_out = pool[["id_grid", "id_grid_asli", "level"] + pre.params["features_in"]].copy()
    for i in range(X.shape[1]):
        pooled_out[f"pc{i + 1}"] = np.round(X[:, i], 6)

    # ── 5. Model final per K keluaran (solusi J terkecil, seed 42–51) ────────
    results["model"] = {}
    pool_labels = {}
    for K in T.K_OUTPUT:
        sol = solutions[K]
        labels, U = T.number_by_travel_time(sol["labels"], sol["U"], pool["waktu_tes_min"].values)
        pool_labels[K] = labels
        centers = T.fuzzy_centers(X, U, cfg.sdwfcm_m)
        desc, pesc = T.desc_pesc(X, labels, A_pool, coords)
        profile = T.cluster_profile(pool, labels, K, t_pen)
        model = {
            "k": K,
            "model_final": {
                "seed_terbaik": sol["seed"], "objective": sol["objective"], "time_sec": sol["time"],
                "pusat_klaster_pca": centers.tolist(),
                "validity": {
                    "iidx": T.i_index(X, labels, centers=centers),
                    "ketegasan_partisi": T.ketegasan_partisi(U, X, cfg.sdwfcm_m),
                    **T.partition_coefficients(U),
                    "dunn": T.dunn_multi(X, labels),
                    "desc": desc,
                    "pesc": pesc,
                    "silhouette_sampel": T.silhouette_sampled(X, labels),
                    "size_entropy": T.size_entropy(labels),
                    "klaster_terbesar_persen": T.largest_cluster_share(labels),
                    "proporsi_tetangga_sama": T.same_label_neighbor_share(labels, A_pool),
                },
            },
            "cluster_profile": profile,
            "cluster_names": {str(r["klaster"]): r["deskripsi"] for r in profile},
            "distribusi": {},
        }
        membership_pool = U.max(axis=1)
        pooled_out[f"klaster_k{K}"] = labels
        pooled_out[f"keanggotaan_maks_k{K}"] = np.round(membership_pool, 6)
        for c in range(K):
            pooled_out[f"u{c}_k{K}"] = np.round(U[:, c], 6)
        states = {}
        for lv in T.LEVELS:
            key = lv["key"]
            df = preps[key]["df"]
            sel = groups == key
            st = T.states_for_level(df, labels[sel], K)
            states[key] = st
            lab = np.where(st < K, st, -1)
            mem = np.full(len(st), np.nan)
            mem[df["tergenang"].values == 0] = membership_pool[sel]
            model["distribusi"][key] = T.level_distribution(st, K)
            grid_parts.append(T.model_grid_frame(key, K, lab, mem, st))
        trans = []
        for a, b in T.TRANSITION_PAIRS:
            tr = T.transition_analysis(states[a], states[b], K)
            tr.update({"from_level": a, "to_level": b})
            trans.append(tr)
        model["transitions"] = trans
        model["cdvm_vs_baseline"] = {key: T.cdvm_distribution(states["baseline"], states[key], K + 1)
                                     for key in T.LEVEL_KEYS}
        results["model"][str(K)] = model
    if 2 in pool_labels and 3 in pool_labels:
        results["tabulasi_silang_k2_k3"] = T.crosstab_labels(pool_labels[2], pool_labels[3], 2, 3)
    t = _tick("model_final_dan_transisi", t)

    # ── 6. Perbandingan algoritma di Baseline untuk setiap K keluaran ─────────
    if not skip_comparison:
        sel = groups == "baseline"
        Wb = W[sel][:, sel]
        for K in T.K_OUTPUT:
            logger.info(f"Perbandingan algoritma (FCM, SFCM, SDWFCM, REDCAP, SKATER) di Baseline, K = {K}...")
            results["model"][str(K)]["algorithm_comparison"] = T.compare_algorithms(
                X[sel], Wb, w, A_rook, K, pool.loc[sel, "waktu_tes_min"].values, cfg)
        t = _tick("perbandingan_algoritma", t)

    timing["total"] = time.time() - t_start
    results["waktu_komputasi"] = timing
    results["elapsed_sec"] = timing["total"]

    out_json = Path(data_dir) / RESULTS_FILE
    out_json.write_text(json.dumps(clean_json(results), ensure_ascii=False, indent=1), encoding="utf-8")
    pd.concat(grid_parts, axis=1).to_csv(Path(data_dir) / GRID_FILE, index=False, compression="gzip")
    pooled_out.to_csv(Path(data_dir) / POOLED_FILE, index=False, compression="gzip")
    logger.info(f"Selesai {time.time() - t_start:.0f}s -> {out_json}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run_thesis_analysis(skip_comparison="--skip-comparison" in sys.argv, force="--force" in sys.argv)

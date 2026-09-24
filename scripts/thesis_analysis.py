"""Analisis offline penelitian (menghasilkan seluruh angka Bab IV).

Menghasilkan:
  data/thesis_results.json         — ringkasan seluruh tabel/metrik Bab IV
  data/thesis_grid_results.csv.gz  — atribut per grid untuk setiap level

Jalankan:  python -m scripts.thesis_analysis   (± 10–15 menit, SFCM paling lama)
           tambahkan --skip-comparison untuk melewati perbandingan algoritma.
"""
import json
import logging
import os
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
    for f in (RESULTS_FILE, GRID_FILE):
        if (lock_dir / f).exists():
            shutil.copy2(lock_dir / f, Path(data_dir) / f)
    return all((Path(data_dir) / f).exists() for f in (RESULTS_FILE, GRID_FILE))


def clean_json(obj):
    if isinstance(obj, dict):
        return {str(k): clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return clean_json(obj.tolist())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if not np.isfinite(v) else round(v, 6)
    return obj


def run_thesis_analysis(data_dir=None, skip_comparison: bool = False, force: bool = False) -> dict:
    t_start = time.time()
    data_dir = data_dir or os.environ.get("SDWFCM_DATA_DIR", str(PROJECT_ROOT / "data"))
    if is_locked(data_dir) and not force:
        restore_locked(data_dir)
        logger.warning("Hasil analisis TERKUNCI (data/locked/LOCK.json) — analisis tidak dijalankan. "
                       "Gunakan --force untuk menimpa.")
        return json.loads((Path(data_dir) / RESULTS_FILE).read_text(encoding="utf-8"))
    cfg = Cfg(base_dir=data_dir)

    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    w = build_weights(gdf)
    A = T.queen_adjacency(gdf)   # blok spasial DESC/PESC
    xy = np.column_stack([gdf["cx"].values, gdf["cy"].values])
    k_final = None   # ditentukan dari skor komposit pada Baseline

    results = {
        "meta": {
            "skenario": T.SKENARIO,
            "levels": T.LEVELS,
            "walking_speed_m_per_min": cfg.walking_speed_m_per_min,
            "sdwfcm": {"m": cfg.sdwfcm_m, "alpha": cfg.sdwfcm_alpha, "knn": cfg.sdwfcm_knn},
            "pca_variance": T.PCA_VARIANCE,
            "iqr_factor": T.IQR_FACTOR,
            "sdwfcm_n_init": T.SDWFCM_N_INIT,
            "feature_labels": T.FEATURE_LABELS,
        },
        "data_summary": {
            "n_grid": int(len(gdf)),
            "n_road_segments": int(len(roads)) if roads is not None else 0,
            "crs": cfg.target_crs,
            "tes_counts": {k: int(len(v)) for k, v in tes.items()},
        },
        "levels": {},
    }
    grid_parts = [pd.DataFrame({
        "id_grid": gdf["id_grid"].values,
        "Road_Density_mean": gdf["Road_Density_mean"].values,
        T.SKENARIO: gdf[T.SKENARIO].values,
    })]

    t_pen = None
    labels_by_level = {}
    for lv in T.LEVELS:
        key = lv["key"]
        logger.info(f"===== LEVEL {lv['label'].upper()} (intensitas {lv['intensity']}) =====")
        prep = T.prepare_level(gdf, roads, tes, lv["intensity"], cfg, t_pen=t_pen)
        t_pen = prep["t_pen"]
        X, df = prep["X"], prep["df"]

        if key == "baseline":
            results["t_pen"] = t_pen
            results["baseline_time_stats"] = T.describe_times(df, cfg)
            logger.info("Evaluasi kandidat K (2–10) pada Baseline...")
            k_rows, k_best = T.evaluate_k_candidates(X, gdf, prep["mask"], A, xy, cfg)
            k_final = k_best
            results["k"] = k_final
            results["k_selection"] = {
                "candidates": k_rows,
                "k_composite_best": k_best,
                "k_selected": k_final,
            }

        cl = T.cluster_level(prep, gdf, cfg, k=k_final)
        labels_by_level[key] = cl["labels"]

        if key == "baseline" and not skip_comparison:
            logger.info("Perbandingan algoritma (SDWFCM, SFCM, REDCAP, SKATER)...")
            results["algorithm_comparison"] = T.compare_algorithms(
                X, gdf, w, k_final, prep["mask"], df["waktu_tes_min"].values, cfg,
                # waktu per inisialisasi agar setara dengan algoritma lain (satu kali jalan)
                sdwfcm_result={"labels": cl["labels"], "time": cl["time"] / T.SDWFCM_N_INIT},
            )

        desc, pesc = T.desc_pesc(X, cl["labels"], A, xy)
        summary = T.level_summary(key, prep, cl, cfg)
        summary["validity"] = {
            "iidx": T.i_index(X, cl["labels"], centers=T.fuzzy_centers(X, cl["U"], cfg.sdwfcm_m)),
            "cdvm": T.membership_distribution_metric(cl["U"], X, cfg.sdwfcm_m),
            "dunn": T.dunn_index(X, cl["labels"]),
            "desc": desc,
            "pesc": pesc,
            "size_entropy": T.size_entropy(cl["labels"]),
        }
        results["levels"][key] = summary
        grid_parts.append(T.level_grid_frame(key, df, cl, cfg))

    trans = []
    for a, b in zip(T.LEVEL_KEYS[:-1], T.LEVEL_KEYS[1:]):
        tr = T.transition_analysis(labels_by_level[a], labels_by_level[b], k_final)
        tr.update({"from_level": a, "to_level": b})
        trans.append(tr)
    results["transitions"] = trans
    results["cdvm_vs_baseline"] = {
        key: T.cdvm_distribution(labels_by_level["baseline"], labels_by_level[key], k_final)
        for key in T.LEVEL_KEYS
    }
    results["elapsed_sec"] = time.time() - t_start

    out_json = Path(data_dir) / RESULTS_FILE
    out_json.write_text(json.dumps(clean_json(results), ensure_ascii=False, indent=1), encoding="utf-8")
    pd.concat(grid_parts, axis=1).to_csv(Path(data_dir) / GRID_FILE, index=False, compression="gzip")
    logger.info(f"Selesai {time.time() - t_start:.0f}s -> {out_json}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run_thesis_analysis(skip_comparison="--skip-comparison" in sys.argv, force="--force" in sys.argv)

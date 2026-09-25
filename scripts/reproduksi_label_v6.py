"""Reproduksi deterministik label yang TIDAK tersimpan di hasil terkunci v6, dengan verifikasi (Finalisasi v6).

    python -m scripts.reproduksi_label_v6

Hasil terkunci hasil-skripsi-v6 hanya menyimpan label K = 2, 3, 4 (data gabungan). Untuk metrik baru
(DESC-N/PESC-N, Bagian B4) dan tabel perbandingan algoritma (Bagian D), label berikut dijalankan ulang dengan
kode, seed, dan data yang sama, lalu DIVERIFIKASI terhadap metrik terkunci (keputusan peneliti Finalisasi v6):
  * SDWFCM data gabungan K = 5..10 (solusi data penuh evaluasi stabilitas, seed 42–51): J, Silhouette, I-Index
    harus sama dengan `k_selection.candidates`; K = 4 juga dijalankan dan harus identik (ARI = 1) dengan label
    terkunci;
  * algoritma pembanding di Baseline (FCM, SFCM, SDWFCM Baseline, REDCAP, SKATER) untuk K = 4 dan K = 2: metrik
    harus sama dengan `model.<K>.algorithm_comparison`.
Praproses di-fit ulang pada data gabungan (deterministik, sama dengan pipeline); parameternya harus sama dengan
parameter terkunci dan skor PCA dibandingkan dengan kolom pc* terkunci.
Bila ada verifikasi yang gagal, skrip berhenti (exit 1) dan label tidak ditulis.

Keluaran (output_bab4/finalisasi_v6/): label_turunan.npz (label mentah) dan verifikasi_label.json.
"""
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

LOCKED = PROJECT_ROOT / "data" / "locked"
OUT = PROJECT_ROOT / "output_bab4" / "finalisasi_v6"
K_REPRO = (4, 5, 6, 7, 8, 9, 10)
K_ALGO = (4, 2)
RTOL = 1e-6          # toleransi relatif verifikasi (angka terkunci dibulatkan 6 desimal)


def close(a, b, rtol=RTOL, atol=2e-6):
    if a is None or b is None:
        return a is None and b is None
    return bool(np.isclose(float(a), float(b), rtol=rtol, atol=atol))


def load_inputs():
    """Data gabungan, X (dihitung ulang dengan praproses terkunci), W blok-diagonal, dan rook."""
    from backend import thesis as T
    from backend.engine import Cfg, build_weights, load_data, load_road_network
    R = json.loads((LOCKED / "thesis_results.json").read_text(encoding="utf-8"))
    cfg = Cfg(base_dir=str(PROJECT_ROOT / "data"))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    w = build_weights(gdf)
    A_rook = T.rook_adjacency(w)
    t_pen, frames = None, {}                       # T_pen dihitung ulang seperti pipeline (nilai JSON dibulatkan)
    for lv in T.LEVELS:
        prep = T.prepare_level(gdf, roads, tes, lv["intensity"], cfg, t_pen=t_pen)
        t_pen = prep["t_pen"]
        frames[lv["key"]] = prep["df"]
    assert abs(t_pen - float(R["t_pen"])) < 1e-6, "T_pen hitung ulang tidak sama dengan T_pen terkunci"
    pool = T.build_pooled(frames, gdf)
    pre = T.Preprocessor.fit(pool, cfg)            # fit ulang (deterministik, sama dengan pipeline); parameter
    X = pre.transform(pool)                        # terkunci dibulatkan 6 desimal sehingga from_dict tidak persis
    from scripts.thesis_analysis import clean_json
    par = json.loads(json.dumps(clean_json(pre.to_dict()), ensure_ascii=False))
    par_beda = sorted(k for k in set(par) | set(R["preprocessing"]) if par.get(k) != R["preprocessing"].get(k))
    par_sama = not par_beda
    locked = pd.read_csv(LOCKED / "thesis_pooled_results.csv.gz")
    pcs = [c for c in locked.columns if c.startswith("pc")]
    same_rows = (np.array_equal(locked["id_grid"].values, pool["id_grid"].values)
                 and np.array_equal(locked["level"].values, pool["level"].values))
    dx = float(np.abs(locked[pcs].values - X).max()) if same_rows else float("inf")
    W, _ = T.block_knn_weights(pool[["cx", "cy"]].values, pool["level"].values, cfg.sdwfcm_knn)
    return R, cfg, gdf, w, A_rook, pool, X, W, locked, {"baris_identik": bool(same_rows), "maks_selisih_pc": dx,
                                                         "parameter_praproses_sama": bool(par_sama),
                                                         "parameter_berbeda": par_beda}


def main():
    from sklearn.metrics import adjusted_rand_score
    from backend import thesis as T
    logging.basicConfig(level=logging.WARNING)
    t0 = time.time()
    R, cfg, gdf, w, A_rook, pool, X, W, locked, ver_x = load_inputs()
    ver = {"X": ver_x, "sdwfcm_gabungan": {}, "algoritma": {}}
    ok = ver_x["baris_identik"] and ver_x["maks_selisih_pc"] < 5e-6 and ver_x["parameter_praproses_sama"]
    print("X:", ver_x, flush=True)
    labels = {}
    cand = {c["k"]: c for c in R["k_selection"]["candidates"]}
    for K in K_REPRO:
        t1 = time.time()
        sol = T.run_sdwfcm(X, W, K, cfg, seeds=T.STABILITY_SEEDS)
        lab = sol["labels"]
        c = cand[K]
        v = {"objective": [sol["objective"], c["objective"]], "seed": [sol["seed"], c["seed_terbaik"]],
             "silhouette": [T.silhouette_sampled(X, lab), c["silhouette"]],
             "iidx": [T.i_index(X, lab, centers=T.fuzzy_centers(X, sol["U"], cfg.sdwfcm_m)), c["iidx"]],
             "detik": time.time() - t1}
        v["cocok"] = (close(*v["objective"]) and v["seed"][0] == v["seed"][1] and close(*v["silhouette"])
                      and close(*v["iidx"], rtol=1e-5))
        if K == 4:
            v["ari_vs_label_terkunci"] = float(adjusted_rand_score(locked["klaster_k4"].values, lab))
            v["cocok"] = v["cocok"] and v["ari_vs_label_terkunci"] == 1.0
        ver["sdwfcm_gabungan"][str(K)] = v
        ok &= v["cocok"]
        print({kk: vv for kk, vv in v.items()}, flush=True)
        labels[f"gabungan_k{K}"] = lab.astype(np.int16)
        print(f"K={K}: cocok={v['cocok']} ({v['detik']:.0f} s)", flush=True)

    sel = pool["level"].values == "baseline"
    Wb = W[sel][:, sel]
    wmin = pool.loc[sel, "waktu_tes_min"].values
    keys = ("silhouette", "calinski_harabasz", "davies_bouldin", "klaster_terbesar_persen", "size_entropy",
            "moran_i", "proporsi_tetangga_sama")
    for K in K_ALGO:
        t1 = time.time()
        runs = T.comparison_runs(X[sel], Wb, w, A_rook, K, wmin, cfg)
        rows = {r["algoritma"]: r for r in T.comparison_rows(runs, X[sel], w, A_rook, wmin)}
        lock_rows = {r["algoritma"]: r for r in R["model"][str(K)]["algorithm_comparison"]}
        vk = {}
        for algo, r in rows.items():
            lr = lock_rows[algo]
            if r["status"] == "gagal" or lr["status"] == "gagal":
                vk[algo] = {"status": [r["status"], lr["status"]], "cocok": r["status"] == lr["status"]}
            else:
                vk[algo] = {kk: [r.get(kk), lr.get(kk)] for kk in keys}
                vk[algo]["status"] = [r["status"], lr["status"]]
                vk[algo]["cocok"] = r["status"] == lr["status"] and all(close(*vk[algo][kk]) for kk in keys)
            ok &= vk[algo]["cocok"]
            if "labels" in runs[algo]:
                labels[f"baseline_k{K}_{algo}"] = T.relabel_by_metric(runs[algo]["labels"], wmin).astype(np.int16)
                labels[f"baseline_k{K}_{algo}_mentah"] = np.asarray(runs[algo]["labels"]).astype(np.int16)
            for extra in ("seed_terbaik", "time_per_init"):
                if extra in runs[algo]:
                    vk[algo][extra] = runs[algo][extra]
        vk["detik"] = time.time() - t1
        ver["algoritma"][str(K)] = vk
        print(f"algoritma K={K}: " + ", ".join(f"{a}={v['cocok']}" for a, v in vk.items() if isinstance(v, dict)),
              flush=True)
    ver["semua_cocok"] = bool(ok)
    ver["detik_total"] = time.time() - t0
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verifikasi_label.json").write_text(json.dumps(ver, indent=1, ensure_ascii=False, default=float),
                                               encoding="utf-8")
    if not ok:
        print("VERIFIKASI GAGAL — label tidak ditulis. Lihat verifikasi_label.json")
        return 1
    np.savez_compressed(OUT / "label_turunan.npz", id_grid=pool["id_grid"].values.astype(np.int32),
                        level=pool["level"].values.astype("U8"), **labels)
    print(f"semua cocok; label ditulis ({ver['detik_total']:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

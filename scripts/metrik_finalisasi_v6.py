"""Metrik Finalisasi v6: diagnostik DESC/PESC asli (B1), DESC-N/PESC-N pada v6 (B4), dan perbandingan algoritma
dengan SDWFCM-Guo (C2, D). Hasil terkunci v6 tidak diubah dan model utama tidak dijalankan ulang.

    python -m scripts.metrik_finalisasi_v6

Masukan:
  data/locked/                                   skor PCA (pc*), label K = 2, 3, 4, metrik terkunci
  output_bab4/finalisasi_v6/label_turunan.npz    label K = 5..10 dan label algoritma pembanding di Baseline,
                                                 hasil scripts/reproduksi_label_v6 (terverifikasi terhadap metrik
                                                 terkunci; verifikasi_label.json harus "semua_cocok")
Keluaran: output_bab4/finalisasi_v6/metrik_finalisasi_v6.json (dibaca scripts/export_bab4.py).

Catatan perhitungan (ditetapkan sebelum dihitung):
  * Ruang fitur = skor PCA terkunci (kolom pc*). Blok spasial = rook di dalam level (data gabungan) atau rook
    Baseline (perbandingan algoritma).
  * I-Index pada tabel perbandingan algoritma memakai centroid tegas untuk SEMUA algoritma (agar setara; algoritma
    non-fuzzy tidak punya pusat fuzzy). Dunn = rerata 5 sampel 2.000 baris (seed 42–46).
  * SDWFCM-Guo: λ = 0,5 bentuk harfiah (tabel utama); varian d², λ = 0,3, dan λ = 0,7 (lampiran). NB = pola tetangga
    W KNN-8 Baseline. 10 inisialisasi seed 42–51, run dengan J_FCM terkecil.
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
DIR = PROJECT_ROOT / "output_bab4" / "finalisasi_v6"
OUT = DIR / "metrik_finalisasi_v6.json"
K_ALGO = (4, 2)
GUO_VARIAN = [("SDWFCM-Guo (d², λ = 0,5)", 0.5, True), ("SDWFCM-Guo (λ = 0,3)", 0.3, False),
              ("SDWFCM-Guo (λ = 0,7)", 0.7, False)]


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def label_metrics(X, lab, A, coords, w_rook, s):
    """Metrik tabel perbandingan untuk satu partisi (label tegas)."""
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
    from backend import desc_n as DN
    from backend import thesis as T
    out = {"klaster_terbesar_persen": T.largest_cluster_share(lab), "size_entropy": T.size_entropy(lab),
           "n_cluster": int(len(np.unique(lab)))}
    if out["n_cluster"] < 2:
        return out
    mi, _ = T.moran_labels(lab, w_rook)
    desc, pesc = T.desc_pesc(X, lab, A, coords)
    n = DN.desc_pesc_n(X, lab, A, coords, s=s)
    out.update({"silhouette": float(silhouette_score(X, lab)), "calinski_harabasz": float(calinski_harabasz_score(X, lab)),
                "davies_bouldin": float(davies_bouldin_score(X, lab)), "moran_i": mi,
                "proporsi_tetangga_sama": T.same_label_neighbor_share(lab, A), "iidx": T.i_index(X, lab),
                "dunn": T.dunn_multi(X, lab)["mean"], "desc": desc, "pesc": pesc, "desc_n": n["desc_n"],
                "pesc_n": n["pesc_n"], "kontiguitas": n["kontiguitas"], "homogenitas": n["homogenitas"],
                "pesc_n_aproksimasi": n["aproksimasi"]})
    return out


def main():
    from sklearn.metrics import adjusted_rand_score
    from backend import desc_n as DN
    from backend import thesis as T
    from backend.engine import Cfg, build_weights, load_data
    from backend.sdwfcm_guo import sdwfcm_guo
    logging.basicConfig(level=logging.WARNING)
    t0 = time.time()
    ver = json.loads((DIR / "verifikasi_label.json").read_text(encoding="utf-8"))
    if not ver.get("semua_cocok"):
        raise SystemExit("verifikasi_label.json tidak 'semua_cocok' — label turunan tidak boleh dipakai.")
    R = json.loads((LOCKED / "thesis_results.json").read_text(encoding="utf-8"))
    pool = pd.read_csv(LOCKED / "thesis_pooled_results.csv.gz")
    lab_t = np.load(DIR / "label_turunan.npz")
    assert np.array_equal(lab_t["id_grid"], pool["id_grid"].values)
    pcs = [c for c in pool.columns if c.startswith("pc")]
    X = pool[pcs].values
    t_pen = float(R["t_pen"])
    cfg = Cfg(base_dir=str(PROJECT_ROOT / "data"))
    gdf = load_data(cfg)
    w = build_weights(gdf)
    A_rook = T.rook_adjacency(w)
    gidx = pool["id_grid"].values.astype(int)
    groups = pool["level"].values
    A_pool = T.block_adjacency(A_rook, gidx, groups)
    coords = np.column_stack([gdf["cx"].values[gidx], gdf["cy"].values[gidx]])
    s = DN.scale_s(X)
    penalti = pool["waktu_tes_min"].values >= t_pen - 1e-3
    res = {"s_gabungan": s, "catatan": __doc__.split("Catatan perhitungan")[1].strip()}

    # ── B1. diagnostik DESC asli ────────────────────────────────────────────
    cand = {c["k"]: c for c in R["k_selection"]["candidates"]}
    labels = {K: pool[f"klaster_k{K}"].values for K in (2, 3, 4)}
    labels.update({K: lab_t[f"gabungan_k{K}"].astype(int) for K in range(5, 11)})
    diag = {"desc_pesc_terkunci": {str(K): {"desc": cand[K]["desc"], "pesc": cand[K]["pesc"]} for K in cand}}
    for K in (3, 4):
        tab = DN.desc_asli_per_blok(X, labels[K], A_pool)
        comp = DN.blocks(labels[K], A_pool)
        pen = pd.Series(penalti).groupby(comp).mean() * 100
        tab["persen_penalti"] = pen
        tab["level"] = pd.Series(groups).groupby(comp).first()
        tot = float(tab["kontribusi"].sum())
        top = tab.sort_values("kontribusi", ascending=False).head(10)
        diag[str(K)] = {
            "desc_dihitung_ulang": tot, "desc_terkunci": cand[K]["desc"], "jumlah_blok": int(len(tab)),
            "jumlah_blok_v_ge_2": int((tab["v"] >= 2).sum()),
            "top10": [{"blok": int(i), "klaster": int(r.klaster), "level": r.level, "v": int(r.v), "V": float(r.V),
                       "d_bar": float(r.d_bar), "kontribusi": float(r.kontribusi),
                       "persen_kontribusi": float(r.kontribusi / tot * 100) if tot else None,
                       "persen_baris_penalti": float(r.persen_penalti)} for i, r in top.iterrows()],
            "persen_desc_dari_blok_dbar_lt_0_01": float(tab.loc[tab["d_bar"] < 0.01, "kontribusi"].sum() / tot * 100),
            "persen_desc_dari_blok_penalti_mayoritas": float(tab.loc[tab["persen_penalti"] > 50, "kontribusi"].sum()
                                                             / tot * 100),
        }
        print(f"B1 K={K}: DESC {tot:.3f} (terkunci {cand[K]['desc']:.3f})", flush=True)
    res["b1_diagnostik_desc"] = diag

    # ── B4. DESC-N / PESC-N pada v6, K = 2..10 ─────────────────────────────
    b4 = {}
    for K in range(2, 11):
        t1 = time.time()
        n = DN.desc_pesc_n(X, labels[K], A_pool, coords, s=s)
        b4[str(K)] = {k: n[k] for k in ("desc_n", "pesc_n", "kontiguitas", "homogenitas", "n_blok", "aproksimasi")}
        b4[str(K)]["pesc_per_klaster"] = n["pesc_per_klaster"]
        b4[str(K)]["detik"] = time.time() - t1
        print(f"B4 K={K}: DESC-N {n['desc_n']:.4f} PESC-N {n['pesc_n']:.4f} ({time.time() - t1:.0f} s)", flush=True)
    res["b4_desc_n_v6"] = b4

    # ── C2/D. perbandingan algoritma di Baseline ────────────────────────────
    sel = groups == "baseline"
    Xb = X[sel]
    gb = gidx[sel]
    assert np.array_equal(gb, np.arange(len(gb))), "baris Baseline harus berurutan id_grid"
    cb = coords[sel]
    Wb, _ = T.block_knn_weights(cb, np.zeros(len(gb), int), cfg.sdwfcm_knn)
    sb = DN.scale_s(Xb)
    wmin = pool.loc[sel, "waktu_tes_min"].values
    res["s_baseline"] = sb
    perb, varian = {}, {}
    for K in K_ALGO:
        lock_rows = {r["algoritma"]: r for r in R["model"][str(K)]["algorithm_comparison"]}
        rows = []
        sd_lab = lab_t[f"baseline_k{K}_SDWFCM"].astype(int)
        guo_runs = {}
        for nama, lam, kuadrat in [("SDWFCM-Guo", 0.5, False)] + GUO_VARIAN:
            t1 = time.time()
            g = sdwfcm_guo(Xb, Wb, K, m=cfg.sdwfcm_m, lam=lam, seeds=T.STABILITY_SEEDS, max_iter=cfg.sdwfcm_max_iter,
                           tol=cfg.sdwfcm_tol, kuadrat=kuadrat)
            lab = T.relabel_by_metric(g["labels"], wmin)
            guo_runs[nama] = {"labels": lab, "g": g}
            print(f"D K={K} {nama}: seed {g['seed']}, konvergen {sum(c['konvergen'] for c in g['konvergensi'])}/10 "
                  f"({time.time() - t1:.0f} s)", flush=True)
        order = ["SDWFCM", "SDWFCM-Guo", "FCM", "SFCM", "REDCAP", "SKATER"]
        for algo in order:
            if algo == "SDWFCM-Guo":
                lab = guo_runs[algo]["labels"]
                g = guo_runs[algo]["g"]
                base = {"algoritma": "SDWFCM-Guo (λ = 0,5)", "n_init": 10, "time_per_init_sec": g["time_per_init"],
                        "seed_terbaik": g["seed"], "J_FCM": g["J_FCM"], "konvergensi": g["konvergensi"]}
            else:
                lr = lock_rows[algo]
                nama = "SDWFCM termodifikasi" if algo == "SDWFCM" else algo
                base = {"algoritma": nama, "n_init": lr.get("n_init"), "time_per_init_sec": lr.get("time_per_init_sec"),
                        "seed_terbaik": lr.get("seed_terbaik")}
                if lr["status"] == "gagal":
                    rows.append({**base, "status": "gagal", "galat": lr.get("galat")})
                    continue
                lab = lab_t[f"baseline_k{K}_{algo}"].astype(int)
            m = label_metrics(Xb, lab, A_rook, cb, w, sb)
            status = "degeneratif" if m["klaster_terbesar_persen"] > T.DEGENERATE_MAX_SHARE * 100 else "ok"
            rows.append({**base, "status": status, **m,
                         "ari_vs_sdwfcm_termodifikasi": float(adjusted_rand_score(sd_lab, lab))})
        perb[str(K)] = rows
        vrows = []
        for nama, lam, kuadrat in GUO_VARIAN:
            lab = guo_runs[nama]["labels"]
            g = guo_runs[nama]["g"]
            m = label_metrics(Xb, lab, A_rook, cb, w, sb)
            vrows.append({"algoritma": nama, "lambda": lam, "kuadrat": kuadrat, "seed_terbaik": g["seed"],
                          "time_per_init_sec": g["time_per_init"], "konvergensi": g["konvergensi"],
                          "status": "degeneratif" if m["klaster_terbesar_persen"] > T.DEGENERATE_MAX_SHARE * 100 else "ok",
                          **m, "ari_vs_sdwfcm_termodifikasi": float(adjusted_rand_score(sd_lab, lab)),
                          "ari_vs_guo_harfiah": float(adjusted_rand_score(guo_runs["SDWFCM-Guo"]["labels"], lab))})
        varian[str(K)] = vrows
    res["d_perbandingan_algoritma"] = perb
    res["d_varian_guo"] = varian
    res["detik_total"] = time.time() - t0
    DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(_clean(res), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"ditulis {OUT} ({res['detik_total']:.0f} s)")


if __name__ == "__main__":
    main()

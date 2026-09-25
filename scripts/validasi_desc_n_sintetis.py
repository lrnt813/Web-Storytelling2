"""Validasi DESC-N dan PESC-N pada data buatan meniru Guo dkk. (2015, hlm. 377–378) — Finalisasi v6 (B3).

    python -m scripts.validasi_desc_n_sintetis

Data: grid 100 × 100 (10.000 sampel, jarak sel 100 m), 4 wilayah kelas tak beraturan (peta deterministik, seed 42:
empat titik pusat acak + distorsi sinusoidal koordinat, kelas = pusat terdekat) dan 4 atribut acak seragam dengan
rentang per kelas persis seperti artikel:
  merah  : a1 0,3–0,8; a2 0,6–0,9; a3 0,1–0,6; a4 0,4–0,9
  kuning : a1 0,0–0,7; a2 0,4–0,8; a3 0,2–0,5; a4 0,6–1,0
  hijau  : a1 0,5–0,8; a2 0,1–0,8; a3 0,2–0,8; a4 0,2–0,7
  biru   : a1 0,1–0,5; a2 0,2–0,6; a3 0,4–0,9; a4 0,1–0,5
Atribut dibangkitkan dengan generator yang sama (RandomState(42)) setelah peta. SDWFCM termodifikasi dijalankan
dengan parameter skripsi (m = 1,7; α = 0,5; W KNN-Gaussian 8 tetangga; 10 inisialisasi seed 42–51; J terkecil)
pada atribut mentah, untuk K = 2..8. Blok spasial = komponen rook.

Kriteria lulus (ditetapkan sebelum dihitung), untuk DESC-N dan PESC-N masing-masing:
  (a) nilai tertinggi di K = 4 ATAU tidak monoton terhadap K;
  (b) invarian terhadap pengalian atribut × 10 (selisih < 1e-9) untuk semua K.

Keluaran: output_bab4/finalisasi_v6/validasi_sintetis.csv, validasi_sintetis.json, peta_data_sintetis.png.
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT = PROJECT_ROOT / "output_bab4" / "finalisasi_v6"
NG = 100
CELL = 100.0
SEED = 42
KELAS = ["merah", "kuning", "hijau", "biru"]
RENTANG = {                     # Guo dkk. (2015), hlm. 377–378
    "merah":  [(0.3, 0.8), (0.6, 0.9), (0.1, 0.6), (0.4, 0.9)],
    "kuning": [(0.0, 0.7), (0.4, 0.8), (0.2, 0.5), (0.6, 1.0)],
    "hijau":  [(0.5, 0.8), (0.1, 0.8), (0.2, 0.8), (0.2, 0.7)],
    "biru":   [(0.1, 0.5), (0.2, 0.6), (0.4, 0.9), (0.1, 0.5)],
}
K_RANGE = range(2, 9)


def rook_grid(n=NG):
    from scipy.sparse import csr_matrix
    idx = np.arange(n * n).reshape(n, n)
    a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    A = csr_matrix((np.ones(2 * len(a)), (np.r_[a, b], np.r_[b, a])), shape=(n * n, n * n))
    rr, cc = np.divmod(np.arange(n * n), n)
    return A, np.column_stack([cc * CELL, rr * CELL])


def make_data(seed=SEED):
    """(kelas benar 0..3, atribut n × 4, koordinat, rook) — deterministik."""
    rng = np.random.RandomState(seed)
    A, coords = rook_grid()
    g = coords / CELL / NG                                  # 0..1
    sites = rng.uniform(0.15, 0.85, size=(4, 2))
    amp, fr, ph = rng.uniform(0.04, 0.09, 3), rng.uniform(2, 6, 3), rng.uniform(0, 2 * np.pi, 6)
    dx = sum(amp[i] * np.sin(2 * np.pi * fr[i] * g[:, 1] + ph[i]) for i in range(3))
    dy = sum(amp[i] * np.sin(2 * np.pi * fr[i] * g[:, 0] + ph[3 + i]) for i in range(3))
    p = np.column_stack([g[:, 0] + dx, g[:, 1] + dy])
    kelas = np.argmin(((p[:, None, :] - sites[None]) ** 2).sum(axis=2), axis=1)
    X = np.empty((len(kelas), 4))
    for c, nama in enumerate(KELAS):
        sel = kelas == c
        for a, (lo, hi) in enumerate(RENTANG[nama]):
            X[sel, a] = rng.uniform(lo, hi, size=int(sel.sum()))
    return kelas, X, coords, A


def monoton(v):
    d = np.diff(np.asarray(v, float))
    return bool((d >= 0).all() or (d <= 0).all())


def main():
    from sklearn.metrics import adjusted_rand_score
    from backend import desc_n as DN
    from backend import thesis as T
    from backend.engine import Cfg
    logging.basicConfig(level=logging.WARNING)
    cfg = Cfg()
    kelas, X, coords, A = make_data()
    W, _ = T.block_knn_weights(coords, np.zeros(len(X), int), cfg.sdwfcm_knn)
    rows = []
    for K in K_RANGE:
        sol = T.run_sdwfcm(X, W, K, cfg, seeds=T.STABILITY_SEEDS)
        lab = sol["labels"]
        desc, pesc = T.desc_pesc(X, lab, A, coords)
        n1 = DN.desc_pesc_n(X, lab, A, coords)
        n10 = DN.desc_pesc_n(X * 10, lab, A, coords)
        rows.append({"K": K, "DESC": desc, "PESC": pesc, "DESC-N": n1["desc_n"], "PESC-N": n1["pesc_n"],
                     "Kontiguitas": n1["kontiguitas"], "Homogenitas": n1["homogenitas"],
                     "I-Index": T.i_index(X, lab, centers=T.fuzzy_centers(X, sol["U"], cfg.sdwfcm_m)),
                     "Dunn": T.dunn_multi(X, lab)["mean"], "Silhouette": T.silhouette_sampled(X, lab),
                     "ARI vs kelas": adjusted_rand_score(kelas, lab), "Jumlah blok": n1["n_blok"],
                     "selisih x10 DESC-N": abs(n1["desc_n"] - n10["desc_n"]),
                     "selisih x10 PESC-N": abs(n1["pesc_n"] - n10["pesc_n"]),
                     "PESC-N aproksimasi": n1["aproksimasi"]})
        print(f"K={K}: " + ", ".join(f"{k}={v:.4f}" for k, v in rows[-1].items() if isinstance(v, float)), flush=True)
    df = pd.DataFrame(rows)
    status = {}
    for m in ("DESC-N", "PESC-N"):
        kmax = int(df.loc[df[m].idxmax(), "K"])
        a = kmax == 4 or not monoton(df[m])
        b = bool((df[f"selisih x10 {m}"] < 1e-9).all())
        status[m] = {"K_tertinggi": kmax, "monoton": monoton(df[m]), "kriteria_a": bool(a), "kriteria_b": b,
                     "lulus": bool(a and b)}
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "validasi_sintetis.csv", index=False, encoding="utf-8-sig")
    (OUT / "validasi_sintetis.json").write_text(json.dumps(
        {"status": status, "ukuran_kelas": {KELAS[c]: int((kelas == c).sum()) for c in range(4)},
         "kriteria": "(a) tertinggi di K = 4 atau tidak monoton; (b) invarian × 10 (< 1e-9)"},
        indent=1, ensure_ascii=False), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(4, 4), dpi=110)
    ax.imshow(kelas.reshape(NG, NG), origin="lower", cmap=ListedColormap(["#dc2626", "#facc15", "#16a34a", "#2563eb"]))
    ax.set_title("Data buatan: 4 wilayah kelas (seed 42)", fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(OUT / "peta_data_sintetis.png")
    plt.close(fig)
    print(json.dumps(status, ensure_ascii=False))
    return df, status


if __name__ == "__main__":
    main()

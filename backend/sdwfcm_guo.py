"""SDWFCM versi asli Guo dkk. (2015) sebagai algoritma PEMBANDING (bukan model utama).

Rujukan: Guo, Y., Liu, K., Wu, Q., Hong, Q., & Zhang, H. (2015). A new spatial fuzzy c-means for spatial
clustering. WSEAS Transactions on Computers, 14, 369–381 (algoritma: hlm. 372, pers. 7–10; λ terbaik: hlm. 375).
Artikel memakai nama SDWFCM dan DWSFCM untuk algoritma yang sama; kriteria henti di artikel = perubahan pusat
klaster (langkah 6), sedangkan di sini disamakan dengan model utama (instruksi Finalisasi v6).

Bentuk harfiah (fungsi `sdwfcm_guo`, `kuadrat=False`):
  pusat (pers. 7)   v_i  = Σ_j u_ij^m x_j / Σ_j u_ij^m
  jarak atribut     d_ij = ‖x_j − v_i‖                     (Euclidean, TIDAK dikuadratkan)
  faktor spasial    f_ij = Σ_{k∈NB(j)} d_ik / min_l Σ_{k∈NB(j)} d_lk      (NB(j) = 8 tetangga terdekat, tanpa bobot)
  jarak gabungan    D_ij = (1 − λ)·d_ij·f_ij + λ·d_ij
  keanggotaan (10)  u_ij = 1 / Σ_k (D_ij / D_kj)^(1/(m−1))   (pangkat harfiah artikel)
Varian `kuadrat=True` (sdwfcm_guo_kuadrat): d_ij diganti ‖x_j − v_i‖² di f dan D (menjawab ambiguitas pangkat;
dengan d² bentuk keanggotaan setara FCM baku).

Artikel tidak merumuskan fungsi objektif, sehingga dari beberapa inisialisasi dipilih run dengan
J_FCM = Σ u^m ‖x − v‖² terkecil (keputusan Finalisasi v6). Inisialisasi dan kriteria henti sama dengan SDWFCM
termodifikasi (engine.SpatialDistanceWeightedFCM): np.random.seed(seed); U ~ Dirichlet(1, …, 1); berhenti bila
‖U_baru − U‖_F < tol atau iterasi maksimum tercapai. Baris tanpa tetangga (NB kosong) mendapat f = 1.
"""
from typing import Dict, List, Optional

import numpy as np
from scipy.sparse import csr_matrix
from scipy.spatial.distance import cdist

LAMBDA_GUO = 0.5          # nilai λ terbaik pada Guo dkk. (2015), hlm. 375


def neighbor_matrix(W: csr_matrix) -> csr_matrix:
    """Matriks ketetanggaan biner NB (tanpa bobot) dari pola non-nol W (KNN-8 model utama)."""
    B = csr_matrix(W, copy=True)
    B.data[:] = 1.0
    B.eliminate_zeros()
    return B


def guo_distances(X: np.ndarray, centers: np.ndarray, NB: csr_matrix, lam: float, kuadrat: bool = False):
    """(d, f, D) berukuran n × K (baris = sampel j, kolom = klaster i)."""
    d = cdist(X, centers)
    if kuadrat:
        d = d ** 2
    d = np.maximum(d, 1e-12)
    S = NB @ d                                     # Σ_{k∈NB(j)} d_ik
    smin = S.min(axis=1, keepdims=True)
    has = np.asarray(NB.sum(axis=1)).ravel() > 0
    f = np.ones_like(d)
    f[has] = S[has] / np.maximum(smin[has], 1e-300)
    D = (1.0 - lam) * d * f + lam * d
    return d, f, D


def membership_from(D: np.ndarray, m: float) -> np.ndarray:
    """u_ij = 1 / Σ_k (D_ij / D_kj)^(1/(m−1))."""
    r = D[:, :, None] / D[:, None, :]
    U = 1.0 / (r ** (1.0 / (m - 1.0))).sum(axis=2)
    return U / U.sum(axis=1, keepdims=True)


def _fit_one(X, NB, k, m, lam, max_iter, tol, seed, kuadrat):
    np.random.seed(seed)
    n = len(X)
    U = np.random.dirichlet(np.ones(k), size=n)
    centers = None
    diff = np.inf
    dc = np.inf
    it = 0
    for it in range(max_iter):
        Um = U ** m
        new_c = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
        dc = np.inf if centers is None else float(np.abs(new_c - centers).max())
        centers = new_c
        _, _, D = guo_distances(X, centers, NB, lam, kuadrat)
        Un = membership_from(D, m)
        diff = float(np.linalg.norm(Un - U))
        U = Un
        if diff < tol:
            break
    Um = U ** m
    centers = (Um.T @ X) / (Um.sum(axis=0)[:, None] + 1e-10)
    j_fcm = float((Um * cdist(X, centers) ** 2).sum())
    return {"seed": int(seed), "U": U, "labels": U.argmax(axis=1).astype(int), "centers": centers,
            "n_iter": int(it + 1), "perubahan_U_akhir": diff, "perubahan_pusat_akhir": dc,
            "konvergen": bool(diff < tol), "J_FCM": j_fcm}


def sdwfcm_guo(X: np.ndarray, W: csr_matrix, k: int, m: float = 1.7, lam: float = LAMBDA_GUO,
               seeds: Optional[List[int]] = None, max_iter: int = 150, tol: float = 1e-4,
               kuadrat: bool = False) -> Dict:
    """SDWFCM Guo dkk. (2015) multi-start. `W` = matriks bobot model utama (hanya pola tetangganya dipakai).
    Mengembalikan run dengan J_FCM terkecil beserta ringkasan konvergensi semua seed."""
    import time
    seeds = list(seeds) if seeds else list(range(42, 52))
    NB = neighbor_matrix(W)
    runs, best = [], None
    for s in seeds:
        t0 = time.time()
        r = _fit_one(np.asarray(X, float), NB, k, m, lam, max_iter, tol, s, kuadrat)
        r["time_sec"] = time.time() - t0
        runs.append(r)
        if best is None or r["J_FCM"] < best["J_FCM"]:
            best = r
    return {**best, "lambda": lam, "kuadrat": kuadrat, "m": m,
            "time_per_init": float(np.mean([r["time_sec"] for r in runs])),
            "konvergensi": [{kk: r[kk] for kk in ("seed", "n_iter", "konvergen", "perubahan_U_akhir",
                                                    "perubahan_pusat_akhir", "J_FCM")} for r in runs],
            "pemilihan_run": "J_FCM = Σ u^m ‖x − v‖² terkecil (artikel tidak merumuskan fungsi objektif)"}


def sdwfcm_guo_kuadrat(X, W, k, **kw):
    """Varian sensitivitas: D dihitung dari d² (lihat docstring modul)."""
    return sdwfcm_guo(X, W, k, kuadrat=True, **kw)


def fcm_literal(X: np.ndarray, k: int, m: float = 1.7, seed: int = 42, max_iter: int = 150, tol: float = 1e-4,
                kuadrat: bool = False) -> Dict:
    """FCM dengan bentuk keanggotaan yang sama (u dari d atau d² dengan pangkat 1/(m−1)); pembanding uji."""
    empty = csr_matrix((len(X), len(X)))
    return _fit_one(np.asarray(X, float), empty, k, m, 0.0, max_iter, tol, seed, kuadrat)

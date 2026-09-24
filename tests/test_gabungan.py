"""Klasterisasi data gabungan (Langkah 6–10 putaran 2)."""
import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix

from backend import thesis as T
from backend.engine import Cfg, SpatialFuzzyCMeans, fuzzy_membership_update


def _pool(n_side=6):
    """Grid n_side × n_side (100 m); Rendah menggenangi 4 grid, Tinggi 10 grid."""
    n = n_side * n_side
    xy = np.array([[100.0 * (i % n_side), 100.0 * (i // n_side)] for i in range(n)])
    gdf = pd.DataFrame({"id_grid": np.arange(n), "id_grid_asli": [f"g{i}" for i in range(n)],
                        "cx": xy[:, 0], "cy": xy[:, 1]})
    wet = {"baseline": [], "rendah": [0, 1, 2, 3], "sedang": [0, 1, 2, 3, 4], "tinggi": list(range(10))}
    frames = {}
    for key, w in wet.items():
        t = np.zeros(n, int)
        t[w] = 1
        frames[key] = pd.DataFrame({"id_grid": np.arange(n), "tergenang": t, "waktu_tes_min": xy[:, 0] / 80})
    return T.build_pooled(frames, gdf), gdf, frames


def test_data_gabungan_tanpa_tergenang():
    pool, gdf, frames = _pool()
    assert len(pool) == 36 + 32 + 31 + 26
    assert list(pool.columns[:3]) == ["id_grid", "id_grid_asli", "level"]
    for key, f in frames.items():
        ids = pool.loc[pool["level"] == key, "id_grid"].values
        assert set(ids) == set(f.loc[f["tergenang"] == 0, "id_grid"])


def test_W_blok_diagonal_dan_baris_berjumlah_satu():
    pool, _, _ = _pool()
    groups = pool["level"].values
    W, sig = T.block_knn_weights(pool[["cx", "cy"]].values, groups, knn=8)
    coo = W.tocoo()
    assert np.all(groups[coo.row] == groups[coo.col]), "ada tetangga lintas level"
    np.testing.assert_allclose(np.asarray(W.sum(axis=1)).ravel(), 1.0, atol=1e-12)
    assert set(sig) == set(T.LEVEL_KEYS)
    assert np.all(np.diff(coo.row[coo.row == 0]) >= 0) and (coo.row != coo.col).all()


def test_ketetanggaan_rook_gabungan_tidak_lintas_level():
    pool, _, _ = _pool()
    n = 36
    rows, cols = [], []
    for i in range(n):
        for j in (i + 1, i + 6):
            if j < n and (j != i + 1 or (i % 6) != 5):
                rows += [i, j]; cols += [j, i]
    A = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    groups = pool["level"].values
    Ap = T.block_adjacency(A, pool["id_grid"].values, groups)
    coo = Ap.tocoo()
    assert np.all(groups[coo.row] == groups[coo.col])
    assert Ap[np.where(groups == "baseline")[0]][:, np.where(groups == "baseline")[0]].nnz == A.nnz


def test_subsampel_membawa_semua_level_grid_terpilih():
    pool, _, _ = _pool()
    masks = T.subsample_masks(pool["id_grid"].values, B=3, frac=0.8, seed0=7)
    for mk in masks:
        chosen = set(pool.loc[mk, "id_grid"])
        assert len(chosen) == round(0.8 * 36)
        assert mk.sum() == pool["id_grid"].isin(chosen).sum()
    again = T.subsample_masks(pool["id_grid"].values, B=3, frac=0.8, seed0=7)
    assert all(np.array_equal(a, b) for a, b in zip(masks, again))


def test_transisi_dengan_state_tergenang():
    K = 2
    a = np.array([0, 0, 1, 1, 0, 1, 2])
    b = np.array([0, 1, 1, 2, 2, 1, 2])       # dua grid masuk Tergenang, satu 0→1
    tr = T.transition_analysis(a, b, K)
    M = np.array(tr["matrix"])
    assert M.shape == (3, 3) and M.sum() == 7
    assert tr["masuk_tergenang"] == 2 and tr["keluar_tergenang"] == 0
    assert tr["n_non_tergenang_kedua_level"] == 4
    assert np.isclose(tr["stability_rate"], 3 / 4 * 100)
    assert tr["dominant_transition"]["menuju"] in (T.TERGENANG, "tipologi lain")
    assert tr["active_edges"] == int(((M - np.diag(np.diag(M))) > 0).sum())
    pa = np.bincount(a, minlength=3) / 7
    pb = np.bincount(b, minlength=3) / 7
    assert np.isclose(tr["cdvm"], 0.5 * np.abs(pa - pb).sum())


def test_aturan_pemilihan_k_toleransi():
    df = pd.DataFrame({"k": [2, 3, 4, 5], "ari_subsampel_mean": [0.950, 0.962, 0.955, 0.70]})
    best = df["ari_subsampel_mean"].max()
    cands = df.loc[df["ari_subsampel_mean"] >= best - T.K_ARI_TOLERANCE, "k"].tolist()
    assert min(cands) == 3          # 0,950 berselisih 0,012 (> 0,01) → K = 2 tidak termasuk


def test_sfcm_vektor_sama_dengan_rumus_loop():
    rng = np.random.default_rng(0)
    n, k, m, alpha = 30, 3, 2.0, 0.5
    X = rng.normal(size=(n, 2))
    adj = [[j for j in (i - 1, i + 1) if 0 <= j < n] for i in range(n)]
    adj[5] = []
    U = rng.dirichlet(np.ones(k), size=n)

    class _W:
        neighbors = {i: adj[i] for i in range(n)}

    from backend.engine import neighbor_mean_operator, sfcm_distances
    R, has = neighbor_mean_operator(_W, n)
    centers, dt = sfcm_distances(X, U, R, has, m, alpha)
    Um = U ** m
    C = (Um.T @ X) / (Um.sum(0)[:, None] + 1e-10)
    da = ((X[:, None] - C[None]) ** 2).sum(-1) + 1e-10
    ds = np.zeros((n, k))
    for i in range(n):
        for c in range(k):
            ds[i, c] = (da[adj[i], c].mean() * U[adj[i]].mean(0)[c]) if adj[i] else da[i, c]
    np.testing.assert_allclose(dt, np.clip((1 - alpha) * da + alpha * ds, 1e-10, None), rtol=1e-10)


def test_penugasan_pusat_tetap():
    rng = np.random.default_rng(1)
    C = np.array([[0.0, 0.0], [5.0, 5.0]])
    X = np.vstack([rng.normal(C[0], 0.3, (20, 2)), rng.normal(C[1], 0.3, (20, 2))])
    groups = np.zeros(40, int)
    coords = np.column_stack([np.arange(40) * 100.0, np.zeros(40)])
    W, _ = T.block_knn_weights(coords, groups, knn=4)
    U = T.assign_to_centers(X, W, C, 1.7, 0.5)
    assert U.argmax(1).tolist() == [0] * 20 + [1] * 20
    np.testing.assert_allclose(U.sum(1), 1.0)


def test_sdwfcm_dengan_W_eksternal_alpha_nol_sama_dengan_fcm():
    from tests.test_sdwfcm import _fcm_reference, _synthetic
    X, coords = _synthetic()
    W, _ = T.block_knn_weights(coords, np.zeros(len(X), int), knn=4)
    cfg = Cfg()
    cfg.sdwfcm_max_iter, cfg.sdwfcm_tol = 25, 0.0
    r = T.run_sdwfcm(X, W, 3, cfg, seeds=[7], alpha=0.0)
    np.testing.assert_allclose(fuzzy_membership_update(np.ones((2, 2)), 1.7), 0.5)
    np.testing.assert_allclose(r["U"], _fcm_reference(X, 3, cfg.sdwfcm_m, 25, 7), atol=1e-6)

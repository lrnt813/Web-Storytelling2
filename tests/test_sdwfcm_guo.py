"""Finalisasi v6: SDWFCM versi asli Guo dkk. (2015) sebagai pembanding."""
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

from backend import sdwfcm_guo as G


def _data(n=120, seed=0):
    rng = np.random.RandomState(seed)
    X = np.vstack([rng.randn(n // 2, 2), rng.randn(n // 2, 2) + 4])
    coords = rng.rand(n, 2) * 1000
    nn = NearestNeighbors(n_neighbors=9).fit(coords)
    _, idx = nn.kneighbors(coords)
    rows = np.repeat(np.arange(n), 8)
    W = csr_matrix((np.full(n * 8, 1 / 8), (rows, idx[:, 1:].ravel())), shape=(n, n))
    return X, W


def test_keanggotaan_berjumlah_satu_dan_konvergen():
    X, W = _data()
    for kuadrat in (False, True):
        r = G.sdwfcm_guo(X, W, 2, seeds=[42, 43], kuadrat=kuadrat)
        assert np.allclose(r["U"].sum(axis=1), 1.0)
        assert len(r["konvergensi"]) == 2 and r["J_FCM"] == min(c["J_FCM"] for c in r["konvergensi"])


def test_f_identik_satu_sama_dengan_fcm_pangkat_sama():
    X, _ = _data()
    kosong = csr_matrix((len(X), len(X)))                 # tanpa tetangga → f ≡ 1
    for kuadrat in (False, True):
        a = G.sdwfcm_guo(X, kosong, 3, seeds=[42], kuadrat=kuadrat)
        b = G.fcm_literal(X, 3, seed=42, kuadrat=kuadrat)
        assert np.allclose(a["U"], b["U"]) and a["n_iter"] == b["n_iter"]


def test_faktor_spasial_rasio_jumlah_jarak_tetangga():
    X = np.array([[0.0], [1.0], [10.0]])
    C = np.array([[0.0], [10.0]])
    NB = csr_matrix(np.array([[0, 1, 0], [1, 0, 0], [0, 1, 0]], float))
    d, f, D = G.guo_distances(X, C, NB, lam=0.5)
    # sampel 0: tetangga {1}: jarak ke pusat 0 = 1, ke pusat 1 = 9 → f = [1, 9]
    assert np.allclose(f[0], [1.0, 9.0])
    assert np.isclose(D[0, 1], 0.5 * 10 * 9 + 0.5 * 10)
    # λ = 1 menghapus faktor spasial (D = d)
    assert np.allclose(G.guo_distances(X, C, NB, lam=1.0)[2], d)


def test_matriks_tetangga_biner_dari_W():
    X, W = _data()
    NB = G.neighbor_matrix(W)
    assert set(np.unique(NB.data)) == {1.0} and (NB.sum(axis=1) == 8).all()

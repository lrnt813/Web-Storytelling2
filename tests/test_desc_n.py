"""Finalisasi v6: DESC-N dan PESC-N (modifikasi Guo dkk., 2015)."""
import numpy as np
from scipy.sparse import csr_matrix

from backend import desc_n as DN
from backend.thesis import desc_pesc


def _rook(nr, nc):
    rows, cols = [], []
    for r in range(nr):
        for c in range(nc):
            i = r * nc + c
            for rr, cc in ((r + 1, c), (r, c + 1)):
                if rr < nr and cc < nc:
                    j = rr * nc + cc
                    rows += [i, j]
                    cols += [j, i]
    A = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(nr * nc, nr * nc))
    coords = np.array([[c * 100.0, r * 100.0] for r in range(nr) for c in range(nc)])
    return A, coords


def _data(seed=0):
    A, coords = _rook(12, 12)
    rng = np.random.RandomState(seed)
    lab = (coords[:, 0] >= 600).astype(int) + 2 * (coords[:, 1] >= 600).astype(int)
    lab[rng.rand(len(lab)) < 0.15] = rng.randint(0, 4, size=None)          # beberapa sel "salah" → blok kecil
    X = rng.rand(len(lab), 3) + lab[:, None] * 0.8
    return X, lab, A, coords


def test_nilai_dalam_selang_0_1():
    X, lab, A, coords = _data()
    r = DN.desc_pesc_n(X, lab, A, coords)
    for key in ("desc_n", "pesc_n", "kontiguitas", "homogenitas"):
        assert 0 < r[key] <= 1, key
    assert r["desc_n"] <= r["kontiguitas"] + 1e-12 and not r["aproksimasi"]


def test_satu_klaster_satu_blok_identik_bernilai_1():
    A, coords = _rook(5, 5)
    X = np.ones((25, 3))
    r = DN.desc_pesc_n(X, np.zeros(25, int), A, coords)
    assert r["desc_n"] == 1.0 and r["pesc_n"] == 1.0 and r["kontiguitas"] == 1.0 and r["homogenitas"] == 1.0


def test_invarian_terhadap_skala_atribut():
    X, lab, A, coords = _data(1)
    a = DN.desc_pesc_n(X, lab, A, coords)
    b = DN.desc_pesc_n(X * 10, lab, A, coords)
    for key in ("desc_n", "pesc_n", "kontiguitas", "homogenitas"):
        assert abs(a[key] - b[key]) < 1e-9


def test_tidak_meledak_bila_d_bar_nol():
    # dua blok beratribut identik per blok (d̄ = 0): DESC asli mengabaikan/meledak, DESC-N tetap ≤ 1
    A, coords = _rook(4, 6)
    lab = (coords[:, 0] >= 300).astype(int)
    X = np.where(lab[:, None] == 1, 5.0, 0.0) * np.ones((24, 2))
    X[0] += 1e-8                                    # d̄ blok kiri sangat kecil tetapi > 0
    r = DN.desc_pesc_n(X, lab, A, coords)
    assert np.isfinite(r["desc_n"]) and 0 < r["desc_n"] <= 1 and 0 < r["pesc_n"] <= 1
    desc, _ = desc_pesc(X, lab, A, coords)
    assert desc > 1e10                              # DESC asli meledak pada d̄ ≈ 0


def test_pesc_n_nilai_manual_dua_blok():
    # satu klaster dengan dua blok tunggal berjarak 300 m: P = (1/3) · g(d/s)
    A, coords = _rook(1, 4)
    lab = np.array([0, 1, 1, 0])
    X = np.array([[0.0], [1.0], [1.0], [2.0]])
    r = DN.desc_pesc_n(X, lab, A, coords)
    s = DN.scale_s(X)
    p0 = (1 / 3) * DN.g(2.0 / s)                   # klaster 0: dua blok tunggal (x = 0 dan x = 300 m)
    assert np.isclose(r["pesc_per_klaster"][0]["P_k"], p0)
    assert np.isclose(r["pesc_n"], 0.5 * p0 + 0.5 * 1.0)


def test_aproksimasi_sampel_mendekati_eksak():
    X, lab, A, coords = _data(2)
    ex = DN.desc_pesc_n(X, lab, A, coords)
    ap = DN.desc_pesc_n(X, lab, A, coords, max_pairs=10, n_sample=20000)
    assert ap["aproksimasi"] and abs(ap["pesc_n"] - ex["pesc_n"]) < 0.02
    assert ap["desc_n"] == ex["desc_n"]


def test_kontribusi_desc_asli_per_blok_sama_dengan_desc():
    X, lab, A, coords = _data(3)
    tab = DN.desc_asli_per_blok(X, lab, A)
    desc, _ = desc_pesc(X, lab, A, coords)
    assert np.isclose(tab["kontribusi"].sum(), desc)

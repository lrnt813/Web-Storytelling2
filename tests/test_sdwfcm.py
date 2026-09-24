"""Uji rumus SDWFCM (Langkah 2 rekonstruksi).

(a) alpha = 0 → SDWFCM harus identik dengan FCM standar (implementasi referensi
    independen di bawah, memakai bentuk baku dengan jarak TAK-kuadrat).
(b) Fungsi objektif J tidak naik antariterasi (dengan toleransi numerik).
"""
import numpy as np
import pytest

from backend.engine import SpatialDistanceWeightedFCM


def _synthetic(n_per=40, seed=0):
    rng = np.random.default_rng(seed)
    means = np.array([[0.0, 0.0], [4.0, 0.5], [1.0, 4.0]])
    X = np.vstack([rng.normal(mu, 0.7, size=(n_per, 2)) for mu in means])
    # koordinat spasial: grid teratur 100 m (unik per titik)
    side = int(np.ceil(np.sqrt(len(X))))
    coords = np.array([[100.0 * (i % side), 100.0 * (i // side)] for i in range(len(X))])
    return X, coords


def _fcm_reference(X, k, m, n_iter, seed):
    """FCM baku (Bezdek): v_k = Σ u^m x / Σ u^m;
    u_ik = 1 / Σ_l (‖x_i − v_k‖ / ‖x_i − v_l‖)^(2/(m−1))."""
    np.random.seed(seed)
    U = np.random.dirichlet(np.ones(k), size=len(X))
    for _ in range(n_iter):
        Um = U ** m
        V = (Um.T @ X) / Um.sum(axis=0)[:, None]
        d = np.sqrt(((X[:, None, :] - V[None, :, :]) ** 2).sum(-1))
        d = np.maximum(d, 1e-12)
        ratio = d[:, :, None] / d[:, None, :]
        U = 1.0 / (ratio ** (2.0 / (m - 1.0))).sum(axis=2)
        U = U / U.sum(axis=1, keepdims=True)
    return U


@pytest.mark.parametrize("m", [1.7, 2.0])
def test_alpha_nol_sama_dengan_fcm_standar(m):
    X, coords = _synthetic()
    k, n_iter, seed = 3, 25, 7
    model = SpatialDistanceWeightedFCM(k=k, m=m, alpha=0.0, knn=4, max_iter=n_iter,
                                       tol=0.0, rs=seed).fit(X, coords)
    U_ref = _fcm_reference(X, k, m, n_iter, seed)
    assert model.n_iter_ == n_iter
    np.testing.assert_allclose(model.U_, U_ref, atol=1e-6)


@pytest.mark.parametrize("alpha", [
    0.0,
    pytest.param(0.5, marks=pytest.mark.xfail(strict=True, reason=(
        "Untuk alpha > 0 suku spasial d_s bergantung pada u^m, sehingga aturan update "
        "keanggotaan bukan peminimum eksak J; penurunan monoton tidak dijamin. "
        "Pada data uji J naik ~1e-7 relatif di beberapa iterasi akhir. "
        "Lihat docs/CATATAN_TEMUAN.md (B2)."))),
])
def test_objektif_tidak_naik(alpha):
    X, coords = _synthetic(seed=1)
    mask = np.zeros(len(X), bool)
    mask[::5] = True  # sebagian grid "terdampak" agar bobot dampak ikut diuji
    model = SpatialDistanceWeightedFCM(k=3, m=1.7, alpha=alpha, knn=4, max_iter=60,
                                       tol=1e-9, rs=3, impact_weight=2.0,
                                       track_objective=True).fit(X, coords, mask_dampak=mask)
    J = np.asarray(model.objective_history_)
    naik = np.diff(J)
    toleransi = 1e-8 * np.abs(J[:-1]) + 1e-10
    assert np.all(naik <= toleransi), (
        f"J naik pada iterasi {np.where(naik > toleransi)[0].tolist()} "
        f"(kenaikan maks {naik.max():.3e})")

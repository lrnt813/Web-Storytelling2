"""Uji aturan penomoran klaster (Langkah 4)."""
import numpy as np
from scipy.sparse import csr_matrix

from backend.thesis import (align_to_baseline, fuzzy_centers, number_by_travel_time,
                            same_label_neighbor_share)


def test_baseline_diurutkan_menurut_waktu_min():
    labels = np.array([0, 0, 1, 1, 2, 2])
    U = np.eye(3)[labels]
    waktu = np.array([30, 32, 5, 6, 12, 11], float)   # klaster lama 1 tercepat, lalu 2, lalu 0
    new_labels, new_U = number_by_travel_time(labels, U, waktu)
    assert new_labels.tolist() == [2, 2, 0, 0, 1, 1]
    np.testing.assert_array_equal(new_U.argmax(1), new_labels)


def test_penyelarasan_ke_pusat_baseline_dan_tanda_tipologi_baru():
    base = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]])
    # level lain: klaster 0 ≈ pusat baseline 2, klaster 1 ≈ baseline 0, klaster 2 jauh (baru)
    X = np.array([[0.1, 9.9], [0.0, 10.1], [0.1, 0.0], [-0.1, 0.1], [40.0, 40.0], [40.2, 39.8]])
    labels = np.array([0, 0, 1, 1, 2, 2])
    U = np.eye(3)[labels] * 0.98 + 0.01
    U /= U.sum(1, keepdims=True)
    new_labels, new_U, info = align_to_baseline(X, labels, U, 1.7, base)
    assert new_labels.tolist() == [2, 2, 0, 0, 1, 1]
    np.testing.assert_array_equal(new_U.argmax(1), new_labels)
    baru = {p["klaster"]: p["tipologi_baru"] for p in info["pasangan"]}
    assert baru == {0: False, 1: True, 2: False}
    np.testing.assert_allclose(fuzzy_centers(X, new_U, 1.7)[2], [0.05, 10.0], atol=0.2)


def test_proporsi_tetangga_sama_tidak_bergantung_penomoran():
    # rantai 0-1-2-3-4-5 (tetangga berurutan)
    r = np.arange(5)
    A = csr_matrix((np.ones(10), (np.r_[r, r + 1], np.r_[r + 1, r])), shape=(6, 6))
    a = np.array([0, 0, 1, 1, 1, 2])
    b = np.array([5, 5, 3, 3, 3, 4])            # penomoran berbeda, partisi sama
    assert same_label_neighbor_share(a, A) == same_label_neighbor_share(b, A) == 3 / 5

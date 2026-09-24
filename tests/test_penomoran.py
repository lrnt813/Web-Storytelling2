"""Uji aturan penomoran klaster: urut naik rata-rata waktu_tes_min (klaster 0 = akses terbaik)."""
import numpy as np
from scipy.sparse import csr_matrix

from backend.thesis import number_by_travel_time, same_label_neighbor_share


def test_baseline_diurutkan_menurut_waktu_min():
    labels = np.array([0, 0, 1, 1, 2, 2])
    U = np.eye(3)[labels]
    waktu = np.array([30, 32, 5, 6, 12, 11], float)   # klaster lama 1 tercepat, lalu 2, lalu 0
    new_labels, new_U = number_by_travel_time(labels, U, waktu)
    assert new_labels.tolist() == [2, 2, 0, 0, 1, 1]
    np.testing.assert_array_equal(new_U.argmax(1), new_labels)


def test_proporsi_tetangga_sama_tidak_bergantung_penomoran():
    # rantai 0-1-2-3-4-5 (tetangga berurutan)
    r = np.arange(5)
    A = csr_matrix((np.ones(10), (np.r_[r, r + 1], np.r_[r + 1, r])), shape=(6, 6))
    a = np.array([0, 0, 1, 1, 1, 2])
    b = np.array([5, 5, 3, 3, 3, 4])            # penomoran berbeda, partisi sama
    assert same_label_neighbor_share(a, A) == same_label_neighbor_share(b, A) == 3 / 5

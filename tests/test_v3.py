"""Putaran 3–4: label peringkat, profil diperkaya, PC/PE, tabulasi silang, m SFCM seragam."""
import numpy as np
import pandas as pd

from backend import thesis as T
from backend.engine import Cfg, SpatialFuzzyCMeans


def test_label_peringkat():
    assert T.rank_label(0, 4) == "Tipologi 1 (terbaik)"
    assert T.rank_label(1, 4) == "Tipologi 2"
    assert T.rank_label(3, 4) == "Tipologi 4 (terburuk)"


def test_profil_penalti_dan_kuantil():
    t_pen = 400.0
    cfg = Cfg()
    n = 8
    df = pd.DataFrame({c: np.arange(n, dtype=float) for c in T.PROFILE_COLS})
    for c in T.TIME_COLS:
        df[c] = [1, 2, 3, 4, t_pen, t_pen, t_pen, 5.0]
    df["is_isolated"] = [0, 0, 0, 0, 1, 1, 1, 0]
    labels = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    prof = T.cluster_profile(df, labels, 2, t_pen)
    a, b = prof
    assert a["waktu_tes_min_median"] == 2.5 and a["waktu_tes_min_n_penalti"] == 0
    assert b["waktu_tes_min_n_penalti"] == 3 and np.isclose(b["waktu_tes_min_persen_penalti"], 75.0)
    assert np.isclose(b["proporsi_terisolasi"], 0.75)
    assert a["deskripsi"] == "Tipologi 1 (terbaik)" and b["deskripsi"] == "Tipologi 2 (terburuk)"
    assert a["waktu_tes_min_p25"] == np.percentile([1, 2, 3, 4], 25)
    assert b["waktu_tes_min_p90"] == np.percentile([t_pen, t_pen, t_pen, 5.0], 90)
    assert np.isclose(b["proporsi_waktu_min_lebih_batas"], 0.75) and a["proporsi_waktu_min_lebih_batas"] == 0
    assert np.isclose(b["proporsi_terputus"], 0.75)


def test_pc_pe():
    U = np.array([[1.0, 0.0], [0.5, 0.5]])
    r = T.partition_coefficients(U)
    assert np.isclose(r["pc"], (1 + 0.5) / 2)
    assert np.isclose(r["pe"], np.log(2) / 2, atol=1e-9)


def test_tabulasi_silang():
    a = np.array([0, 0, 1, 1, 1])
    b = np.array([0, 1, 2, 2, 1])
    ct = T.crosstab_labels(a, b, 2, 3)
    assert ct["matrix"] == [[1, 1, 0], [0, 1, 2]]


def test_m_sfcm_seragam():
    cfg = Cfg()
    assert not hasattr(cfg, "sfcm_m")
    assert SpatialFuzzyCMeans().m == cfg.sdwfcm_m == 1.7
    assert tuple(T.K_OUTPUT) == (2, 3, 4)

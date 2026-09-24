"""Uji pra-pemrosesan (Langkah 3): transform dari parameter JSON = pipeline sklearn,
dan level lain memakai parameter Baseline tanpa fit ulang."""
import json

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import PowerTransformer, RobustScaler

from backend.engine import Cfg
from backend.thesis import IQR_FACTOR, PCA_VARIANCE, Preprocessor, feature_columns


def _df(seed=0, n=500, shift=0.0):
    rng = np.random.default_rng(seed)
    cfg = Cfg()
    d = {"Road_Density_mean": rng.lognormal(0, 0.8, n)}
    for k in cfg.kategori_fac:
        d[f"waktu_tes_{k}"] = rng.gamma(2.0, 8.0, n) + shift
    d["waktu_tes_min"] = np.min([d[f"waktu_tes_{k}"] for k in cfg.kategori_fac], axis=0)
    d["jumlah_opsi_rute"] = rng.integers(3, 6, n).astype(float)
    d["is_isolated"] = (rng.random(n) < 0.05).astype(float)
    d["banjir"] = rng.integers(0, 4, n).astype(float)
    return pd.DataFrame(d), cfg


def test_transform_sama_dengan_sklearn():
    df, cfg = _df()
    pre = Preprocessor.fit(df, cfg)
    X = pre.transform(df)

    F = df[feature_columns(cfg)].astype(float).copy()
    q1, q3 = np.percentile(F["Road_Density_mean"], [25, 75])
    F["Road_Density_mean"] = np.clip(F["Road_Density_mean"], q1 - IQR_FACTOR * (q3 - q1), q3 + IQR_FACTOR * (q3 - q1))
    Fk = F[pre.params["features_kept"]].values
    Z = RobustScaler().fit_transform(PowerTransformer(method="yeo-johnson").fit_transform(Fk))
    ref = PCA(n_components=PCA_VARIANCE, svd_solver="full").fit_transform(Z)
    np.testing.assert_allclose(X, ref, atol=1e-8)


def test_parameter_baseline_dipakai_ulang_dan_bisa_diserialisasi():
    base, cfg = _df(seed=1)
    other, _ = _df(seed=2, shift=30.0)          # level lain: waktu tempuh lebih lama
    pre = Preprocessor.fit(base, cfg)
    pre2 = Preprocessor.from_dict(json.loads(json.dumps(pre.to_dict())))
    np.testing.assert_allclose(pre.transform(other), pre2.transform(other), atol=1e-12)
    # tidak ada fit ulang: dimensi & fitur mengikuti Baseline
    assert pre2.transform(other).shape[1] == pre.params["n_components"]
    # hanya Road_Density_mean yang di-capping
    assert list(pre.params["caps"]) == ["Road_Density_mean"]

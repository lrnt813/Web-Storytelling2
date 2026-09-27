"""Penggabungan data penduduk per kalurahan ke KulonProgo_Desa.gpkg dan peta sebarannya."""
import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from scripts import penduduk_desa as P


def _desa():
    # dua kotak 1 km × 1 km dan 2 km × 1 km di UTM 49S
    g = gpd.GeoDataFrame({"NAMOBJ": ["Wates", "Temon  Kulon"]},
                         geometry=[box(400000, 9120000, 401000, 9121000), box(402000, 9120000, 404000, 9121000)],
                         crs=P.CRS_UTM)
    return g.to_crs("EPSG:4326")


def test_normalisasi_nama():
    assert P.normalisasi_nama("Kelurahan Wates") == "wates"
    assert P.normalisasi_nama(" Temon  Kulon ") == "temon kulon"


def test_gabung_penduduk_dan_kepadatan():
    csv = pd.DataFrame({"Kalurahan/Village": ["temon kulon", "Wates"], "Penduduk": [1000, 500]})
    h = P.gabung_penduduk(_desa(), csv)
    assert list(h["penduduk"]) == [500, 1000]
    assert np.allclose(h["luas_km2"], [1.0, 2.0], rtol=1e-3)
    assert np.allclose(h["kepadatan_jiwa_km2"], [500, 500], rtol=1e-3)


def test_nama_tidak_cocok_dihentikan():
    csv = pd.DataFrame({"Kalurahan/Village": ["Wates", "Glagah"], "Penduduk": [1, 2]})
    with pytest.raises(ValueError, match="tidak cocok"):
        P.gabung_penduduk(_desa(), csv)


def test_kelas_kuantil_dan_peta(tmp_path):
    b = P.kelas_kuantil(np.arange(1, 11))
    assert len(b) == P.N_KELAS + 1 and b[0] == 1 and b[-1] == 10
    g = P.gabung_penduduk(_desa(), pd.DataFrame({"Kalurahan/Village": ["Wates", "Temon Kulon"], "Penduduk": [5, 9]}))
    f = tmp_path / "desa.gpkg"
    g.to_file(f, layer="KulonProgo_Desa", driver="GPKG")
    out = P.peta_sebaran_penduduk(f, tmp_path / "peta.png", kec=tmp_path / "tidak_ada.gpkg")
    assert out.exists() and out.stat().st_size > 0

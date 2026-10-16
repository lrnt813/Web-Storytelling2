"""Kelengkapan kartografis peta: batas kabupaten, arah utara, dan skala batang."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
from matplotlib.patches import Rectangle

from scripts import peta_util as P


def test_panjang_skala_bulat_dan_tidak_melebihi_porsi():
    assert P.panjang_skala(26_000) == 5000          # 25 % dari 26 km = 6,5 km → 5 km
    assert P.panjang_skala(1_000) == 250
    assert P.panjang_skala(900, porsi=0.3) == 250   # 270 m → 250 m
    for w in (130, 777, 4321, 61_000):
        L = P.panjang_skala(w)
        assert L <= 0.25 * w
        assert L / 10 ** int(f"{L:e}".split("e")[1]) in P.LANGKAH_SKALA


def test_label_jarak():
    assert P._label_jarak(5000) == "5 km" and P._label_jarak(2500) == "2,5 km" and P._label_jarak(250) == "250 m"


def _ax(w=1000, h=600):
    fig, ax = plt.subplots()
    ax.plot([0, w], [0, h])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    return fig, ax


@pytest.mark.parametrize("luar", [False, True])
def test_lengkapi_peta_menambah_utara_dan_skala_tanpa_mengubah_batas_sumbu(luar):
    fig, ax = _ax()
    P.lengkapi_peta(ax, batas=False, luar=luar)
    assert ax.get_xlim() == (0, 1000) and ax.get_ylim() == (0, 600)
    assert any(t.get_text() == "U" for t in ax.texts)                       # arah utara
    bar = [p for p in ax.patches if isinstance(p, Rectangle)]
    assert len(bar) == 2 and sum(p.get_width() for p in bar) == P.panjang_skala(1000, 0.3 if luar else 0.25)
    if luar:                                                                # di bawah bingkai, tidak menutupi isi
        assert all(p.get_y() < 0 for p in bar)
    plt.close(fig)


def test_batas_kabupaten_satu_poligon_utm():
    b = P.batas_kabupaten()
    if b is None:
        pytest.skip("data/KulonProgo_Kec.gpkg tidak tersedia")
    assert len(b) == 1 and b.crs.to_epsg() == 32749
    assert 5e8 < b.area.iloc[0] < 6.5e8                                     # Kulon Progo ± 586 km²


def test_batas_kabupaten_tidak_mengubah_batas_sumbu_yang_sudah_ditetapkan():
    if P.batas_kabupaten() is None:
        pytest.skip("data/KulonProgo_Kec.gpkg tidak tersedia")
    fig, ax = _ax()
    ax.set_xlim(400_000, 401_000)
    ax.set_ylim(9_130_000, 9_130_600)
    P.gambar_batas_kabupaten(ax)
    assert ax.get_xlim() == (400_000, 401_000) and ax.get_ylim() == (9_130_000, 9_130_600)
    plt.close(fig)

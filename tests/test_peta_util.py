"""Kelengkapan kartografis peta: batas kabupaten, arah utara, dan skala batang."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
from matplotlib.patches import Rectangle

from scripts import peta_util as P


def test_panjang_skala_bulat_dan_tidak_melebihi_porsi():
    assert P.panjang_skala(26_000, 0.25) == 5000    # 6,5 km → 5 km
    assert P.panjang_skala(1_000, 0.25) == 250
    assert P.panjang_skala(900, porsi=0.3) == 250   # 270 m → 250 m
    for w in (130, 777, 4321, 61_000):
        L = P.panjang_skala(w)
        assert L <= w
        assert L / 10 ** int(f"{L:e}".split("e")[1]) in P.LANGKAH_SKALA


def test_label_jarak():
    assert P._label_jarak(5000) == "5 km" and P._label_jarak(2500) == "2,5 km" and P._label_jarak(250) == "250 m"


def test_tata_letak_panel_terpisah_dari_peta():
    fig, peta, panel = P.tata_letak(2)
    assert len(peta) == 2 and set(panel) == {"mata_angin", "legenda", "skala"}
    kanan_peta = max(ax.get_position().x1 for ax in peta)
    assert all(ax.get_position().x0 > kanan_peta for ax in panel.values())   # panel tidak menimpa peta
    ys = [panel[n].get_position() for n in ("mata_angin", "legenda", "skala")]
    assert ys[0].y0 >= ys[1].y1 and ys[1].y0 >= ys[2].y1                     # urutan atas → bawah, tidak bertumpuk
    assert "info" in P.tata_letak(info=1.0)[2]
    plt.close("all")


def test_selesaikan_mata_angin_lengkap_legenda_dan_skala():
    fig, (ax,), panel = P.tata_letak()
    ax.plot([0, 20_000], [0, 30_000])
    ax.set_xlim(0, 20_000)
    ax.set_ylim(0, 30_000)
    from matplotlib.patches import Patch
    L = P.selesaikan(fig, [ax], panel, [Patch(color="red", label="Label yang cukup panjang untuk dibungkus otomatis")],
                     "Judul", batas=False)
    assert ax.get_xlim() == (0, 20_000) and ax.get_ylim() == (0, 30_000)
    huruf = {t.get_text() for t in panel["mata_angin"].texts}
    assert huruf == {"U", "T", "S", "B"}                                     # empat arah utama
    lg = panel["legenda"].get_legend()
    assert lg is not None and lg.get_title().get_text() == "Judul"
    assert max(len(b) for t in lg.get_texts() for b in t.get_text().splitlines()) \
        <= P.lebar_karakter(panel["legenda"], 7.5)
    bar = [p for p in panel["skala"].patches if isinstance(p, Rectangle)]
    assert len(bar) == 4 and L in {1000 * m * 10 ** e for m in P.LANGKAH_SKALA for e in range(-3, 3)}
    assert any(t.get_text() == P.KETERANGAN_PROYEKSI for t in panel["skala"].texts)
    plt.close(fig)


def test_skala_sesuai_ukuran_peta_di_kertas():
    fig, (ax,), panel = P.tata_letak()
    ax.set_xlim(0, 10_000)
    ax.set_ylim(0, 10_000)
    L = P.gambar_skala(fig, ax, panel["skala"])
    ax.apply_aspect()
    w = fig.get_size_inches()[0]
    m_per_inci = 10_000 / (ax.get_position().width * w)
    lebar_bar_inci = sum(p.get_width() for p in panel["skala"].patches) * panel["skala"].get_position().width * w
    assert abs(lebar_bar_inci * m_per_inci - L) / L < 1e-6                  # panjang batang = L meter pada skala peta
    plt.close(fig)


def test_sesuaikan_rasio_memperluas_tanpa_menggeser_pusat():
    x0, x1, y0, y1 = P.sesuaikan_rasio(0, 1000, 0, 100)
    assert (x0, x1) == (0, 1000) and abs((y1 - y0) / 1000 - 0.72) < 1e-9 and (y0 + y1) / 2 == 50
    x0, x1, y0, y1 = P.sesuaikan_rasio(0, 100, 0, 1000)
    assert abs((y1 - y0) / (x1 - x0) - 1.35) < 1e-9 and (x0 + x1) / 2 == 50
    assert P.sesuaikan_rasio(0, 100, 0, 100) == (0, 100, 0, 100)


def test_batas_kabupaten_satu_poligon_utm():
    b = P.batas_kabupaten()
    if b is None:
        pytest.skip("data/KulonProgo_Kec.gpkg tidak tersedia")
    assert len(b) == 1 and b.crs.to_epsg() == 32749
    assert 5e8 < b.area.iloc[0] < 6.5e8                                     # Kulon Progo ± 586 km²


def test_batas_kabupaten_tidak_mengubah_batas_sumbu_yang_sudah_ditetapkan():
    if P.batas_kabupaten() is None:
        pytest.skip("data/KulonProgo_Kec.gpkg tidak tersedia")
    fig, ax = plt.subplots()
    ax.set_xlim(400_000, 401_000)
    ax.set_ylim(9_130_000, 9_130_600)
    P.gambar_batas_kabupaten(ax)
    assert ax.get_xlim() == (400_000, 401_000) and ax.get_ylim() == (9_130_000, 9_130_600)
    plt.close(fig)

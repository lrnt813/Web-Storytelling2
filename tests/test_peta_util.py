"""Sistem desain kartografi (scripts/peta_util.py): format angka, tata letak tetap, legenda, skala, dan palet."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from scripts import peta_util as P


def test_format_angka_indonesia_dan_label_hitung():
    assert P.angka(22673) == "22.673" and P.angka(2.5, 1) == "2,5"
    assert P.persen(7175, 22673) == "31,6%"
    assert P.label_hitung("Tergenang", 7175, 22673) == "Tergenang — 7.175 (31,6%)"
    assert P._label_jarak(5000) == "5 km" and P._label_jarak(2500) == "2,5 km" and P._label_jarak(250) == "250 m"


def test_panjang_skala_bulat_dan_tidak_melebihi_porsi():
    assert P.panjang_skala(26_000, 0.25) == 5000
    assert P.panjang_skala(900, porsi=0.3) == 250
    for w in (130, 777, 4321, 61_000):
        L = P.panjang_skala(w)
        assert L <= w and L / 10 ** int(f"{L:e}".split("e")[1]) in P.LANGKAH_SKALA


def test_sesuaikan_rasio_memperluas_tanpa_menggeser_pusat():
    x0, x1, y0, y1 = P.sesuaikan_rasio(0, 1000, 0, 100)
    assert (x0, x1) == (0, 1000) and abs((y1 - y0) / 1000 - 0.72) < 1e-9 and (y0 + y1) / 2 == 50
    x0, x1, y0, y1 = P.sesuaikan_rasio(0, 100, 0, 1000)
    assert abs((y1 - y0) / (x1 - x0) - 1.35) < 1e-9 and (x0 + x1) / 2 == 50


def test_kanvas_ukuran_tetap_dan_panel_tidak_menimpa_peta():
    a = P.kanvas(1, 1.26)
    b = P.kanvas(1, 1.26)
    assert tuple(a[0].get_size_inches()) == tuple(b[0].get_size_inches())          # peta sejenis berukuran sama
    assert a[0].get_size_inches()[0] == P.LEBAR_FIG and a[0].dpi == P.DPI == 300
    fig, peta, panel = P.kanvas(2, 1.0, judul_peta=True)
    assert len(peta) == 2 and max(ax.get_position().x1 for ax in peta) < panel.get_position().x0
    assert peta[0].get_position().x1 < peta[1].get_position().x0
    plt.close("all")


def _kanvas_terisi():
    fig, (ax,), panel = P.kanvas(1, 1.0)
    ax.plot([0, 10_000], [0, 10_000])
    P.atur_batas(ax, 0, 10_000, 0, 10_000)
    return fig, ax, panel


def test_legenda_berkelompok_dibungkus_dan_disusun_ke_bawah():
    fig, ax, panel = _kanvas_terisi()
    h1 = [P.kotak("#fed98e", "Label kategori yang cukup panjang sehingga harus dibungkus otomatis — 1.234 (5,4%)")]
    y = P.legenda(panel, [("Kelompok utama", h1), ("Referensi", [P.handle_batas_kab()])], "Catatan angka.")
    assert 0 < y < 1
    lgs = [a for a in panel.artists if isinstance(a, matplotlib.legend.Legend)]
    assert [lg.get_title().get_text() for lg in lgs] == ["Kelompok utama", "Referensi"]
    n = P._lebar_karakter(panel, P.FS_LABEL)
    assert all(len(b) <= n for lg in lgs for t in lg.get_texts() for b in t.get_text().splitlines())
    r = fig.canvas.get_renderer()
    assert lgs[0].get_window_extent(r).y0 > lgs[1].get_window_extent(r).y1               # tidak bertumpuk
    plt.close(fig)


def test_blok_bawah_arah_utara_skala_dan_proyeksi():
    fig, ax, panel = _kanvas_terisi()
    y_blok = P.blok_bawah(panel, ax, "Sumber: uji")
    teks = [" ".join(t.get_text().split()) for t in panel.texts]
    assert "U" in teks and any(P.KETERANGAN_PROYEKSI in t for t in teks)
    bar = [p for p in panel.patches if isinstance(p, Rectangle)]
    assert len(bar) == 2 and 0 < y_blok < 0.6
    # panjang batang di kertas = L meter pada skala peta
    u = fig._peta_ukuran
    L = P.panjang_skala(10_000 / u["w"] * 0.55 * u["lebar_panel"])
    lebar_inci = sum(p.get_width() for p in bar) * u["lebar_panel"]
    assert abs(lebar_inci * 10_000 / u["w"] - L) / L < 1e-9
    plt.close(fig)


def _luminansi(c):
    r, g, b = [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in to_rgb(c)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@pytest.mark.parametrize("ramp", [*P.TIPOLOGI.values(), *P.PENDUDUK.values()])
def test_palet_berurutan_terang_ke_gelap(ramp):
    lum = [_luminansi(c) for c in ramp]
    assert all(a > b for a, b in zip(lum, lum[1:]))


def test_biru_hanya_untuk_banjir():
    """Warna dengan rona biru dominan hanya dipakai untuk genangan/ruas ditutup banjir."""
    import colorsys

    def biru(c):
        h, s_, v = colorsys.rgb_to_hsv(*to_rgb(c))
        return s_ > 0.25 and 185 <= h * 360 <= 245
    semua = {**P.WARNA, **{f"tip{k}_{i}": c for k, r in P.TIPOLOGI.items() for i, c in enumerate(r)},
             **{f"pend_{k}_{i}": c for k, r in P.PENDUDUK.items() for i, c in enumerate(r)}}
    assert {k for k, c in semua.items() if biru(c)} <= {"tergenang", "tergenang_latar", "jalan_tutup"}


def test_batas_kabupaten_satu_poligon_utm():
    b = P.batas_kabupaten()
    if b is None:
        pytest.skip("data/KulonProgo_Kec.gpkg tidak tersedia")
    assert len(b) == 1 and b.crs.to_epsg() == 32749 and 5e8 < b.area.iloc[0] < 6.5e8
    x0, x1, y0, y1 = P.batas_tampilan_kabupaten(1.26)
    bx0, by0, bx1, by1 = b.total_bounds
    assert x0 < bx0 and x1 > bx1 and y0 < by0 and y1 > by1 and np.isclose((y1 - y0) / (x1 - x0), 1.26)

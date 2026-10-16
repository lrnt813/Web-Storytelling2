"""Kelengkapan kartografis peta keluaran: batas Kabupaten Kulon Progo, arah utara, dan skala batang.

Peta digambar pada EPSG:32749 (UTM 49S, satuan meter) sehingga skala batang dapat dihitung langsung dari koordinat.
Batas kabupaten = gabungan (dissolve) batas kapanewon di data/KulonProgo_Kec.gpkg (BIG 1:10.000). Modul ini hanya
mengubah tampilan peta; tidak membaca maupun mengubah hasil analisis.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEC = PROJECT_ROOT / "data" / "KulonProgo_Kec.gpkg"
CRS_PETA = "EPSG:32749"
WARNA_BATAS = "#18181b"
LANGKAH_SKALA = (1, 2, 2.5, 5)


@lru_cache(maxsize=1)
def batas_kabupaten(kec: str = str(KEC)):
    """Poligon Kabupaten Kulon Progo (GeoSeries satu baris, EPSG:32749); None bila berkas tidak ada."""
    import geopandas as gpd
    if not Path(kec).exists():
        return None
    g = gpd.read_file(kec).to_crs(CRS_PETA)
    return gpd.GeoSeries([g.geometry.union_all()], crs=CRS_PETA)


def panjang_skala(lebar_peta_m: float, porsi: float = 0.25) -> float:
    """Panjang skala batang (m) yang 'bulat' (1, 2, 2,5, atau 5 × 10^n), tidak melebihi porsi × lebar peta."""
    target = max(float(lebar_peta_m) * porsi, 1e-9)
    e = 10 ** np.floor(np.log10(target))
    return float(max(m * e for m in LANGKAH_SKALA if m * e <= target))


def _label_jarak(m: float) -> str:
    if m >= 1000:
        v = m / 1000
        return (f"{v:g}".replace(".", ",")) + " km"
    return f"{m:g}".replace(".", ",") + " m"


def gambar_batas_kabupaten(ax, lebar: float = 1.0, warna: str = WARNA_BATAS, label: bool = False):
    """Garis batas kabupaten; batas sumbu (xlim/ylim) yang sudah ada dipertahankan."""
    b = batas_kabupaten()
    if b is None:
        return None
    xl, yl, auto = ax.get_xlim(), ax.get_ylim(), ax.get_autoscale_on()
    h = b.boundary.plot(ax=ax, color=warna, linewidth=lebar, zorder=6,
                        label="Batas Kabupaten Kulon Progo" if label else None)
    if ax.has_data() and not auto:
        ax.set_xlim(xl)
        ax.set_ylim(yl)
    return h


def handle_batas(lebar: float = 1.0):
    """Entri legenda untuk garis batas kabupaten."""
    from matplotlib.lines import Line2D
    return Line2D([], [], color=WARNA_BATAS, linewidth=lebar, label="Batas Kabupaten Kulon Progo")


def tambah_skala(ax, x: float = 0.96, y: float = 0.04, porsi: float = 0.25, fontsize: float = 6.5,
                 label_tengah: bool = True):
    """Skala batang dua segmen (hitam-putih) berujung kanan di (x, y) dalam koordinat pecahan sumbu. y < 0
    menempatkan skala di bawah bingkai peta (di luar area peta)."""
    from matplotlib.patches import Rectangle
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    W, H = x1 - x0, y1 - y0
    L = panjang_skala(W, porsi)
    xe = x0 + x * W
    xs, yb, tinggi = xe - L, y0 + y * H, 0.012 * H
    for i in range(2):
        ax.add_patch(Rectangle((xs + i * L / 2, yb), L / 2, tinggi, facecolor="black" if i == 0 else "white",
                               edgecolor="black", linewidth=0.6, zorder=10, clip_on=False))
    label = [(xs, "0")] + ([(xs + L / 2, _label_jarak(L / 2).split(" ")[0])] if label_tengah else [])         + [(xe, _label_jarak(L))]
    for xv, t in label:
        ax.text(xv, yb + tinggi + 0.008 * H, t, ha="center", va="bottom", fontsize=fontsize, color="black",
                zorder=10, clip_on=False)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    return L


def tambah_arah_utara(ax, x: float = 0.06, y: float = 0.86, panjang: float = 0.07, fontsize: float = 9):
    """Panah utara (huruf U) dengan pangkal di (x, y) pecahan sumbu (boleh di luar bingkai). Pada UTM 49S, utara
    grid ≈ utara sebenarnya (konvergensi meridian di Kulon Progo < 0,2°)."""
    ax.annotate("U", xy=(x, y + panjang), xytext=(x, y), xycoords="axes fraction", textcoords="axes fraction",
                ha="center", va="top", fontsize=fontsize, fontweight="bold", zorder=11, annotation_clip=False,
                arrowprops=dict(facecolor="black", edgecolor="black", width=2.5, headwidth=8, headlength=8))


def lengkapi_peta(ax, batas: bool = True, utara=(0.06, 0.86), skala=(0.96, 0.04), lebar_batas: float = 1.0,
                  luar: bool = False):
    """Batas kabupaten + arah utara + skala batang. Dipanggil setelah semua lapisan digambar.
    luar=True (peta lokal yang isinya bisa di mana saja): arah utara dan skala diletakkan di bawah bingkai peta
    agar tidak menutupi isi; posisi `utara`/`skala` diabaikan."""
    ax.set_aspect("equal")
    if batas:
        gambar_batas_kabupaten(ax, lebar=lebar_batas)
    if luar:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        tambah_skala(ax, 1.0, -0.075, porsi=0.3 if (x1 - x0) >= (y1 - y0) else 0.55, label_tengah=False)
        tambah_arah_utara(ax, 0.03, -0.12, panjang=0.075, fontsize=7.5)
    else:
        tambah_skala(ax, *skala)
        tambah_arah_utara(ax, *utara)

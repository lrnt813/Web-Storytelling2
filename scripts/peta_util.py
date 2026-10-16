"""Tata letak dan kelengkapan kartografis peta keluaran: bingkai peta, panel samping (mata angin, legenda, skala
batang, keterangan proyeksi), dan batas Kabupaten Kulon Progo.

Susunan setiap peta:
    ┌───────────────────────────┐ ┌──────────────┐
    │                           │ │  mata angin  │
    │          peta             │ ├──────────────┤
    │   (di dalam bingkai)      │ │   legenda    │
    │                           │ ├──────────────┤
    │                           │ │ skala batang │
    └───────────────────────────┘ └──────────────┘
Elemen pendukung tidak pernah digambar di atas peta, sehingga tidak menutupi isi dan tidak berdempetan.

Peta digambar pada EPSG:32749 (UTM 49S, meter); skala batang dihitung dari ukuran peta setelah tata letak final,
sehingga tetap benar bila gambar diperbesar/diperkecil (skala grafis, bukan angka 1 : N). Batas kabupaten =
gabungan batas kapanewon data/KulonProgo_Kec.gpkg (BIG 1:10.000). Modul ini hanya mengubah tampilan peta.
"""
import textwrap
from functools import lru_cache
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEC = PROJECT_ROOT / "data" / "KulonProgo_Kec.gpkg"
CRS_PETA = "EPSG:32749"
KETERANGAN_PROYEKSI = "Proyeksi: UTM zona 49S (WGS 84)"
WARNA_BATAS = "#18181b"
WARNA_BINGKAI = "#52525b"
LANGKAH_SKALA = (1, 2, 2.5, 5)
ARAH = (("U", 90), ("T", 0), ("S", 270), ("B", 180))        # Utara, Timur, Selatan, Barat


# ── data ────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def batas_kabupaten(kec: str = str(KEC)):
    """Poligon Kabupaten Kulon Progo (GeoSeries satu baris, EPSG:32749); None bila berkas tidak ada."""
    import geopandas as gpd
    if not Path(kec).exists():
        return None
    g = gpd.read_file(kec).to_crs(CRS_PETA)
    return gpd.GeoSeries([g.geometry.union_all()], crs=CRS_PETA)


def panjang_skala(lebar_m: float, porsi: float = 1.0) -> float:
    """Panjang skala (m) yang 'bulat' (1, 2, 2,5, atau 5 × 10^n), tidak melebihi porsi × lebar_m."""
    target = max(float(lebar_m) * porsi, 1e-9)
    e = 10 ** np.floor(np.log10(target))
    return float(max(m * e for m in LANGKAH_SKALA if m * e <= target))


def _label_jarak(m: float, satuan: bool = True) -> str:
    v, s = (m / 1000, "km") if m >= 1000 else (m, "m")
    t = f"{v:g}".replace(".", ",")
    return f"{t} {s}" if satuan else t


def bungkus(label: str, lebar: int = 32) -> str:
    """Label legenda panjang dipecah beberapa baris agar muat di panel."""
    return "\n".join(textwrap.wrap(str(label), lebar)) or str(label)


def handle_batas(lebar: float = 1.2):
    """Entri legenda untuk garis batas kabupaten."""
    from matplotlib.lines import Line2D
    return Line2D([], [], color=WARNA_BATAS, linewidth=lebar, label="Batas Kabupaten Kulon Progo")


# ── tata letak ──────────────────────────────────────────────────────────────
def tata_letak(n_peta: int = 1, ukuran=(10.0, 7.8), dpi: int = 130, lebar_peta: float = 2.7, lebar_panel: float = 1.0,
               tinggi_panel=(1.05, 3.0, 0.75), info: float = 0.0, atas: float = 0.9, bawah: float = 0.04):
    """Figure dengan n_peta sumbu peta berbingkai dan satu panel samping.

    Returns (fig, daftar sumbu peta, panel) dengan panel = {"mata_angin", "legenda", "skala"} (+ "info" bila
    info > 0, disisipkan di antara legenda dan skala). Semua sumbu panel tanpa sumbu koordinat."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    fig = plt.figure(figsize=ukuran, dpi=dpi)
    gs = fig.add_gridspec(1, n_peta + 1, width_ratios=[lebar_peta] * n_peta + [lebar_panel], left=0.025,
                          right=0.975, top=atas, bottom=bawah, wspace=0.05)
    peta = [fig.add_subplot(gs[0, i]) for i in range(n_peta)]
    nama = ["mata_angin", "legenda"] + (["info"] if info else []) + ["skala"]
    tinggi = list(tinggi_panel[:2]) + ([info] if info else []) + [tinggi_panel[2]]
    sub = gs[0, -1].subgridspec(len(nama), 1, height_ratios=tinggi, hspace=0.04)
    panel = {n: fig.add_subplot(sub[i, 0]) for i, n in enumerate(nama)}
    for ax in panel.values():
        ax.set_axis_off()
    # bingkai panel (satu kotak membungkus seluruh panel) dan garis pemisah antarbagian
    pos = gs[0, -1].get_position(fig)
    fig.patches.append(FancyBboxPatch((pos.x0, pos.y0), pos.width, pos.height, boxstyle="square,pad=0",
                                      transform=fig.transFigure, fill=False, edgecolor=WARNA_BINGKAI, linewidth=0.8))
    for atas_, bawah_ in zip(nama[:-1], nama[1:]):
        y = (panel[atas_].get_position().y0 + panel[bawah_].get_position().y1) / 2
        fig.add_artist(plt.Line2D([pos.x0, pos.x1], [y, y], transform=fig.transFigure, color="#d4d4d8", linewidth=0.6))
    for ax in peta:
        siapkan_peta(ax)
    if n_peta == 1:
        peta[0].set_anchor("E")                                # peta merapat ke panel (rasio 1 : 1 menyisakan ruang)
    return fig, peta, panel


def siapkan_peta(ax):
    """Sumbu peta: rasio 1 : 1, tanpa label koordinat, dengan bingkai (neatline)."""
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_edgecolor(WARNA_BINGKAI)
        s.set_linewidth(0.8)


def gambar_batas_kabupaten(ax, lebar: float = 1.2, warna: str = WARNA_BATAS):
    """Garis batas kabupaten; batas sumbu yang sudah ditetapkan (set_xlim/set_ylim) dipertahankan."""
    b = batas_kabupaten()
    if b is None:
        return None
    xl, yl, auto = ax.get_xlim(), ax.get_ylim(), ax.get_autoscale_on()
    h = b.boundary.plot(ax=ax, color=warna, linewidth=lebar, zorder=6)
    if not auto:
        ax.set_xlim(xl)
        ax.set_ylim(yl)
    return h


def beri_ruang(ax, pad: float = 0.04):
    """Ruang kosong di sekeliling isi peta agar tidak menempel pada bingkai."""
    ax.margins(pad)
    ax.autoscale_view()


# ── elemen panel ────────────────────────────────────────────────────────────
def gambar_mata_angin(ax, fontsize: float = None):
    """Mata angin delapan arah: empat arah utama (U, T, S, B) berujung hitam-putih dan empat arah antara.
    Pada UTM 49S utara grid ≈ utara sebenarnya (konvergensi meridian di Kulon Progo < 0,2°)."""
    from matplotlib.patches import Circle, Polygon
    if fontsize is None:                                       # huruf menyesuaikan tinggi ruang mata angin
        tinggi_pt = ax.get_position().height * ax.figure.get_size_inches()[1] * 72
        fontsize = float(np.clip(tinggi_pt / 11, 6.5, 10))
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.75, 1.75)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.add_patch(Circle((0, 0), 0.62, fill=False, edgecolor="#71717a", linewidth=0.6, zorder=1))
    for k in range(4):                                         # arah antara (TL, TG, BD, BL)
        a = np.deg2rad(45 + 90 * k)
        tip, kiri, kanan = (0.62 * np.cos(a), 0.62 * np.sin(a)), (0.12 * np.cos(a + np.pi / 2), 0.12 * np.sin(a + np.pi / 2)), \
            (0.12 * np.cos(a - np.pi / 2), 0.12 * np.sin(a - np.pi / 2))
        ax.add_patch(Polygon([tip, kiri, (0, 0), kanan], closed=True, facecolor="#a1a1aa", edgecolor="#52525b",
                             linewidth=0.5, zorder=2))
    for huruf, deg in ARAH:                                    # arah utama, setiap ujung dibelah hitam/putih
        a = np.deg2rad(deg)
        tip = (np.cos(a), np.sin(a))
        sisi = [(0.2 * np.cos(a + s * np.pi / 2), 0.2 * np.sin(a + s * np.pi / 2)) for s in (1, -1)]
        ax.add_patch(Polygon([(0, 0), tip, sisi[0]], closed=True, facecolor="black", edgecolor="black",
                             linewidth=0.6, zorder=3))
        ax.add_patch(Polygon([(0, 0), tip, sisi[1]], closed=True, facecolor="white", edgecolor="black",
                             linewidth=0.6, zorder=3))
        ax.text(1.3 * np.cos(a), 1.3 * np.sin(a), huruf, ha="center", va="center", fontsize=fontsize,
                fontweight="bold" if huruf == "U" else "normal", color="#18181b")


def lebar_karakter(ax, fontsize: float) -> int:
    """Perkiraan jumlah karakter label legenda yang muat di lebar sumbu panel (setelah ruang simbol)."""
    lebar_pt = ax.get_position().width * ax.figure.get_size_inches()[0] * 72
    return max(14, int((lebar_pt - 34) / (fontsize * 0.56)))


def tulis_legenda(ax, handles, judul=None, fontsize: float = 7.5, y: float = 0.98, **kw):
    """Legenda di panel (rata kiri-atas, tanpa kotak; panel sudah berbingkai). Label dibungkus otomatis sesuai
    lebar panel."""
    if not handles:
        return None
    n = lebar_karakter(ax, fontsize)
    for h in handles:
        h.set_label(bungkus(" ".join(h.get_label().split()), n))
    lg = ax.legend(handles=handles, title=judul, loc="upper left", bbox_to_anchor=(0.04, y), frameon=False,
                   fontsize=fontsize, title_fontsize=fontsize + 0.5, alignment="left", borderaxespad=0.2,
                   handlelength=1.6, labelspacing=0.55, **kw)
    if lg.get_title():
        lg.get_title().set_fontweight("bold")
    return lg


def gambar_skala(fig, ax_peta, ax, porsi: float = 0.78, fontsize: float = 7, keterangan: str = KETERANGAN_PROYEKSI):
    """Skala batang empat segmen di sumbu panel `ax`, dihitung dari skala sumbu peta `ax_peta` setelah tata letak
    final (rasio 1 : 1 diterapkan). Returns panjang skala (m)."""
    from matplotlib.patches import Rectangle
    ax_peta.apply_aspect()
    p_peta, p_skala = ax_peta.get_position(), ax.get_position()
    w_fig = fig.get_size_inches()[0]
    x0, x1 = ax_peta.get_xlim()
    m_per_inci = (x1 - x0) / (p_peta.width * w_fig)
    lebar_panel_inci = p_skala.width * w_fig
    L = panjang_skala(m_per_inci * lebar_panel_inci, porsi)
    f = L / m_per_inci / lebar_panel_inci                       # panjang skala dalam pecahan lebar panel
    xs, yb, h = (1 - f) / 2, 0.42, 0.11
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    for i in range(4):
        ax.add_patch(Rectangle((xs + i * f / 4, yb), f / 4, h, facecolor="black" if i % 2 == 0 else "white",
                               edgecolor="black", linewidth=0.6, transform=ax.transAxes))
    for i, t in ((0, "0"), (2, _label_jarak(L / 2, False)), (4, _label_jarak(L))):
        ax.text(xs + i * f / 4, yb + h + 0.06, t, ha="center", va="bottom", fontsize=fontsize, transform=ax.transAxes)
    ax.text(0.5, 0.93, "Skala", ha="center", va="top", fontsize=fontsize + 0.5, fontweight="bold",
            transform=ax.transAxes)
    if keterangan:
        ax.text(0.5, 0.2, keterangan, ha="center", va="center", fontsize=fontsize - 0.8, color="#52525b",
                transform=ax.transAxes)
    return L


def selesaikan(fig, peta, panel, handles=None, judul_legenda=None, batas: bool = True, fontsize_legenda=7.5,
               legenda_y: float = 0.98, legenda_kw=None):
    """Lengkapi peta: batas kabupaten (+ entri legenda), mata angin, legenda, dan skala batang."""
    handles = list(handles or [])
    if batas and batas_kabupaten() is not None:
        for ax in peta:
            gambar_batas_kabupaten(ax)
        handles.append(handle_batas())
    gambar_mata_angin(panel["mata_angin"])
    tulis_legenda(panel["legenda"], handles, judul_legenda, fontsize_legenda, legenda_y, **(legenda_kw or {}))
    return gambar_skala(fig, peta[0], panel["skala"])


def judul(fig, peta, panel, teks: str, fontsize: float = 10.5, y: float = 0.965):
    """Judul di tengah gabungan bingkai peta dan panel (bukan tengah figure, yang bergeser setelah dipangkas)."""
    peta[0].apply_aspect()
    x = (peta[0].get_position().x0 + panel["skala"].get_position().x1) / 2
    fig.suptitle(teks, x=x, y=y, fontsize=fontsize, fontweight="bold")


def handles_rute(baseline: bool = False):
    """Entri legenda peta lokal rute TAS (lembar validasi dan dampak koreksi snapping)."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    h = [Patch(facecolor="#a855f7", alpha=0.35, edgecolor="#6b21a8", label="Grid TAS"),
         Line2D([], [], marker="*", color="#16a34a", linestyle="none", markersize=10, label="TES terdekat"),
         Line2D([], [], color="#111827", linestyle=":", linewidth=1.2, label="Garis lurus grid ke TES"),
         Line2D([], [], color="#2563eb", linewidth=1.6, label="Rute jaringan jalan"),
         Line2D([], [], color="#f97316", linewidth=1.4, linestyle="--", label="Ruas snapping"),
         Line2D([], [], color="#9ca3af", linewidth=0.8, label="Jalan")]
    if baseline:
        h += [Line2D([], [], color="#dc2626", linewidth=0.9, linestyle="--", label="Ruas ditutup banjir"),
              Line2D([], [], color="#0d9488", linewidth=2.6, alpha=0.55, label="Rute Baseline (sebelum banjir)")]
    return h


def tinggi_pas(lebar_fig: float, rasio_hw: float, n_peta: int = 1, lebar_peta: float = 2.7, lebar_panel: float = 1.0,
               atas: float = 0.9, bawah: float = 0.04, minimum: float = 3.9, maksimum: float = 8.0) -> float:
    """Tinggi figure (inci) agar bingkai peta dengan rasio tinggi/lebar `rasio_hw` setinggi panel di sampingnya."""
    lebar_peta_inci = lebar_fig * 0.95 * lebar_peta / (n_peta * lebar_peta + lebar_panel) * 0.97
    return float(np.clip(lebar_peta_inci * rasio_hw / (atas - bawah), minimum, maksimum))


def sesuaikan_rasio(x0, x1, y0, y1, rmin: float = 0.72, rmax: float = 1.35):
    """Perluas batas peta (tetap berpusat sama) agar rasio tinggi/lebar di antara rmin dan rmax: peta lokal yang
    sangat lebar/tinggi tetap sejajar dengan panel dan menampilkan konteks jalan di sekitarnya."""
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if h / w < rmin:
        h = w * rmin
    elif h / w > rmax:
        w = h / rmax
    return cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2

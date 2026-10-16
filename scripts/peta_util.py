"""Sistem desain kartografi untuk seluruh peta keluaran (Bab IV, lampiran validasi, dampak koreksi snapping).

Hanya mengatur tampilan: tidak membaca, mengubah, atau menghitung ulang hasil analisis. Data, geometri, kelas, dan CRS
(EPSG:32749) dipakai apa adanya dari kode pemanggil.

Tata letak (lebar figure tetap 7 inci; skala yang sama untuk semua peta saat dimasukkan ke halaman A4):

    Judul utama (fenomena)                                     ← 10,5 pt tebal
    Subjudul (skenario, ambang, parameter)                     ← 8 pt abu-abu
    ┌────────────────────────────────────┐  Kelompok legenda 1 ← judul kelompok 7,5 pt tebal
    │                                    │    ■ kategori — n (p%)  7 pt
    │                peta                │  Kelompok legenda 2
    │   (batas tampilan sama untuk       │    …
    │    semua peta kabupaten)           │  ▲U   0  2,5  5 km     ← arah utara sederhana + skala
    │                                    │  Proyeksi … / sumber   ← 6 pt abu-abu
    └────────────────────────────────────┘

Warna mengikuti makna (diuji keterbedaannya untuk penglihatan normal, deuteranopia, dan protanopia dengan jarak
OKLab): biru hanya untuk genangan; abu-abu untuk area tanpa analisis atau grid tanpa kategori; urutan
(tipologi, kategori akses, kelas penduduk) memakai gradasi satu arah terang → gelap; kategori nominal memakai warna
yang tidak menyiratkan urutan. Kategori yang sama memakai warna yang sama di semua peta.
"""
import textwrap
from functools import lru_cache
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEC = PROJECT_ROOT / "data" / "KulonProgo_Kec.gpkg"
CRS_PETA = "EPSG:32749"
DPI = 300

# ── tipografi (satu keluarga huruf, hierarki ukuran) ────────────────────────
FONT = "DejaVu Sans"
FS_JUDUL, FS_SUBJUDUL, FS_JUDUL_PETA = 10.5, 8.0, 8.0
FS_KELOMPOK, FS_LABEL, FS_TEKNIS = 7.5, 7.0, 6.0
WARNA_TEKS, WARNA_TEKS_2 = "#1f1f1f", "#5f5f5f"

# ── warna semantik ──────────────────────────────────────────────────────────
WARNA = {
    "luar_grid": "#f4f4f2",        # di dalam kabupaten, di luar grid analisis / tidak diklasterkan
    "grid_lain": "#c8c8c8",        # grid analisis tanpa kategori yang disorot (Non-TAS, bukan TAS, lainnya)
    "tergenang": "#5b9bd5",        # genangan banjir (satu-satunya pemakaian biru)
    "tergenang_latar": "#a9cbe8",  # Tergenang pada peta yang tidak mengklasterkannya (biru sama, lebih lembut)
    "tak_terjangkau": "#7f2f0a",   # tidak terjangkau lewat jaringan jalan (bukan hitam: batas wilayah gelap)
    "tas": "#aa4499",              # Titik Aman Semu
    "dipicu": "#d55e00",           # muncul/dipicu oleh banjir
    "diperparah": "#e69f00",       # diperparah oleh banjir
    "tak_teratribusi": "#5e5e5e",  # "lainnya": penyebab tidak dapat diatribusikan (netral gelap)
    "terjangkau": "#a1d99b",       # ≤ batas waktu evakuasi
    "jauh": "#f28e2b",             # > batas waktu evakuasi
    "batas_kab": "#2b2b2b",
    "batas_kec": "#8a8a8a",
    "bingkai": "#6e6e6e",
    "jalan": "#c5c7ca",
    "rute": "#d55e00",
    "rute_baseline": "#7a7a7a",
    "jalan_tutup": "#2f6fb3",      # ruas ditutup banjir (keluarga biru = banjir)
    "tes": "#009e73",
}
LEBAR_BATAS_KAB, LEBAR_BATAS_KEC = 0.8, 0.4
# Gradasi berurutan (ColorBrewer YlOrBr): Tipologi 1 = akses terbaik (terang) → Tipologi K = terburuk (gelap)
TIPOLOGI = {2: ["#fed98e", "#993404"], 3: ["#fed98e", "#fe9929", "#993404"],
            4: ["#fed98e", "#fe9929", "#d95f0e", "#993404"]}
PENDUDUK = {"jumlah": ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"],     # ColorBrewer Purples
            "kepadatan": ["#feedde", "#fdbe85", "#fd8d3c", "#e6550d", "#a63603"]}  # ColorBrewer Oranges
LANGKAH_SKALA = (1, 2, 2.5, 5)

# ── tata letak (inci) ───────────────────────────────────────────────────────
LEBAR_FIG = 7.0
MARGIN = 0.14
LEBAR_PANEL = 2.05
JARAK = 0.18
TINGGI_JUDUL = 0.62
TINGGI_JUDUL_PETA = 0.36
TINGGI_BLOK_BAWAH = 0.78         # arah utara + skala + keterangan proyeksi/sumber
RUANG_SIMBOL_PT = 32             # lebar simbol + jarak di depan label legenda (poin)
KETERANGAN_PROYEKSI = "Proyeksi: WGS 84 / UTM zona 49S (EPSG:32749)"
SUMBER_BATAS = "Batas administrasi: BIG, skala 1:10.000"


# ── format angka Indonesia ──────────────────────────────────────────────────
def angka(v, dec: int = 0) -> str:
    s = f"{float(v):,.{dec}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def persen(n, total, dec: int = 1) -> str:
    return f"{angka(100 * n / total, dec)}%" if total else "–"


def label_hitung(nama: str, n, total, satuan: str = "") -> str:
    """'Nama — 1.234 (5,4%)' dari data (jumlah dan persentase dihitung, tidak ditulis tangan)."""
    return f"{nama} — {angka(n)}{(' ' + satuan) if satuan else ''} ({persen(n, total)})"


def _label_jarak(m: float, satuan: bool = True) -> str:
    v, s = (m / 1000, "km") if m >= 1000 else (m, "m")
    t = angka(v, 0 if float(v).is_integer() else 1)
    return f"{t} {s}" if satuan else t


def panjang_skala(lebar_m: float, porsi: float = 1.0) -> float:
    """Panjang skala (m) yang 'bulat' (1, 2, 2,5, atau 5 × 10^n), tidak melebihi porsi × lebar_m."""
    target = max(float(lebar_m) * porsi, 1e-9)
    e = 10 ** np.floor(np.log10(target))
    return float(max(m * e for m in LANGKAH_SKALA if m * e <= target))


# ── data referensi ──────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def batas_kabupaten(kec: str = str(KEC)):
    """Poligon Kabupaten Kulon Progo (gabungan batas kapanewon BIG; GeoSeries satu baris, EPSG:32749)."""
    import geopandas as gpd
    if not Path(kec).exists():
        return None
    g = gpd.read_file(kec).to_crs(CRS_PETA)
    return gpd.GeoSeries([g.geometry.union_all()], crs=CRS_PETA)


@lru_cache(maxsize=1)
def batas_kapanewon(kec: str = str(KEC)):
    import geopandas as gpd
    return gpd.read_file(kec).to_crs(CRS_PETA) if Path(kec).exists() else None


def batas_tampilan_kabupaten(rasio_hw: float, pad_m: float = 900.0):
    """Batas tampilan tetap untuk semua peta kabupaten: kotak batas kabupaten + pad, diperluas ke rasio bingkai."""
    b = batas_kabupaten()
    x0, y0, x1, y1 = b.total_bounds
    return sesuaikan_rasio(x0 - pad_m, x1 + pad_m, y0 - pad_m, y1 + pad_m, rasio_hw, rasio_hw)


def sesuaikan_rasio(x0, x1, y0, y1, rmin: float = 0.72, rmax: float = 1.35):
    """Perluas batas (pusat tetap) agar rasio tinggi/lebar berada di [rmin, rmax]."""
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if h / w < rmin:
        h = w * rmin
    elif h / w > rmax:
        w = h / rmax
    return cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2


# ── simbol legenda ──────────────────────────────────────────────────────────
def kotak(warna: str, label: str, tepi: str = "#8a8a8a", **kw):
    from matplotlib.patches import Patch
    return Patch(facecolor=warna, edgecolor=tepi, linewidth=0.4, label=label, **kw)


def garis(warna: str, label: str, lebar: float = 1.0, gaya: str = "-", **kw):
    from matplotlib.lines import Line2D
    return Line2D([], [], color=warna, linewidth=lebar, linestyle=gaya, label=label, **kw)


def titik(warna: str, label: str, penanda: str = "*", ukuran: float = 8, **kw):
    from matplotlib.lines import Line2D
    return Line2D([], [], color=warna, marker=penanda, linestyle="none", markersize=ukuran,
                  markeredgecolor="#1f1f1f", markeredgewidth=0.4, label=label, **kw)


def handle_batas_kab():
    return garis(WARNA["batas_kab"], "Batas kabupaten", LEBAR_BATAS_KAB + 0.2)


def handle_batas_kec():
    return garis(WARNA["batas_kec"], "Batas kapanewon", LEBAR_BATAS_KEC + 0.2)


# ── kanvas ──────────────────────────────────────────────────────────────────
def kanvas(n_peta: int = 1, rasio_hw: float = 1.3, judul_peta: bool = False, lebar_panel: float = LEBAR_PANEL):
    """Figure berukuran tetap: n_peta bingkai peta (rasio tinggi/lebar sama) + panel kanan.

    Returns (fig, daftar sumbu peta, sumbu panel). Ukuran dihitung dalam inci sehingga peta sejenis selalu
    memiliki ukuran figure dan posisi elemen yang identik."""
    import matplotlib.pyplot as plt
    tersedia = LEBAR_FIG - 2 * MARGIN - lebar_panel - JARAK - (n_peta - 1) * JARAK
    w = tersedia / n_peta
    h = w * rasio_hw
    tj = TINGGI_JUDUL_PETA if judul_peta else 0.0
    H = MARGIN + h + tj + TINGGI_JUDUL + MARGIN
    fig = plt.figure(figsize=(LEBAR_FIG, H), dpi=DPI)
    fig.patch.set_facecolor("white")
    fx, fy = (lambda v: v / LEBAR_FIG), (lambda v: v / H)
    peta = []
    for i in range(n_peta):
        ax = fig.add_axes([fx(MARGIN + i * (w + JARAK)), fy(MARGIN), fx(w), fy(h)])
        _bingkai(ax)
        peta.append(ax)
    x_panel = MARGIN + n_peta * w + n_peta * JARAK
    panel = fig.add_axes([fx(x_panel), fy(MARGIN), fx(lebar_panel), fy(h + tj)])
    panel.set_axis_off()
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)
    fig._peta_ukuran = dict(H=H, h=h, w=w, tj=tj, x_panel=x_panel, lebar_panel=lebar_panel)
    return fig, peta, panel


def _bingkai(ax):
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_edgecolor(WARNA["bingkai"])
        s.set_linewidth(0.6)


def atur_batas(ax, x0, x1, y0, y1):
    """Batas tampilan peta tepat sesuai bingkai (rasio sudah disesuaikan pemanggil)."""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)


def judul(fig, utama: str, sub: str = ""):
    """Judul utama (fenomena) dan subjudul (skenario/parameter), rata kiri pada tepi bingkai peta."""
    u = fig._peta_ukuran
    x = MARGIN / LEBAR_FIG
    y = 1 - MARGIN / u["H"]
    fig.text(x, y, utama, ha="left", va="top", fontsize=FS_JUDUL, fontweight="bold", color=WARNA_TEKS, family=FONT)
    if sub:
        lebar = int((LEBAR_FIG - 2 * MARGIN) * 72 / (FS_SUBJUDUL * 0.52))
        fig.text(x, y - 0.24 / u["H"], textwrap.fill(sub, lebar), ha="left", va="top", fontsize=FS_SUBJUDUL,
                 color=WARNA_TEKS_2, family=FONT, linespacing=1.3)


def judul_peta(ax, teks: str):
    """Judul kecil di atas satu bingkai (peta berdampingan)."""
    u = ax.figure._peta_ukuran
    teks = textwrap.fill(teks, int(u["w"] * 72 / (FS_JUDUL_PETA * 0.55)))
    ax.set_title(teks, fontsize=FS_JUDUL_PETA, color=WARNA_TEKS, pad=4, loc="left", family=FONT, linespacing=1.15)


# ── lapisan referensi ───────────────────────────────────────────────────────
def latar_kabupaten(ax, warna: str = WARNA["luar_grid"]):
    """Isi wilayah kabupaten dengan warna netral (di bawah grid): area tanpa grid analisis tidak tampil putih."""
    b = batas_kabupaten()
    if b is not None:
        b.plot(ax=ax, color=warna, linewidth=0, zorder=0)


def gambar_batas(ax, kapanewon: bool = False):
    if kapanewon and batas_kapanewon() is not None:
        batas_kapanewon().boundary.plot(ax=ax, color=WARNA["batas_kec"], linewidth=LEBAR_BATAS_KEC, zorder=5)
    b = batas_kabupaten()
    if b is not None:
        b.boundary.plot(ax=ax, color=WARNA["batas_kab"], linewidth=LEBAR_BATAS_KAB, zorder=6)


def isi_grid(ax, gdf, warna, tonjolkan: bool = False, zorder: int = 2):
    """Poligon grid dengan warna per baris. Tepi diberi warna yang sama (lebar sangat tipis) agar tidak muncul garis
    putih antargrid; tonjolkan=True menebalkan tepi untuk kategori yang jarang (TAS) agar tetap terlihat saat
    diperkecil — hanya simbolisasi, geometri tidak berubah."""
    if len(gdf) == 0:
        return
    gdf.plot(ax=ax, color=warna, edgecolor=warna, linewidth=0.55 if tonjolkan else 0.08, zorder=zorder)


# ── panel ───────────────────────────────────────────────────────────────────
def _lebar_karakter(panel, fontsize: float) -> int:
    lebar_pt = panel.get_position().width * panel.figure.get_size_inches()[0] * 72
    return max(16, int((lebar_pt - RUANG_SIMBOL_PT) / (fontsize * 0.55)))


def legenda(panel, kelompok, catatan: str = "", y_awal: float = 1.0):
    """Legenda berkelompok, disusun dari atas panel. kelompok = [(judul_kelompok, [handle, ...]), ...].
    Label dibungkus sesuai lebar panel. Returns posisi bawah legenda (pecahan sumbu panel)."""
    fig = panel.figure
    renderer = fig.canvas.get_renderer()
    y = y_awal
    if catatan:
        t = panel.text(0.0, y, textwrap.fill(catatan, _lebar_karakter(panel, FS_TEKNIS) + 6), ha="left", va="top",
                       fontsize=FS_TEKNIS, color=WARNA_TEKS_2, transform=panel.transAxes, linespacing=1.3)
        bb = t.get_window_extent(renderer).transformed(panel.transAxes.inverted())
        y = bb.y0 - 0.025
    n = _lebar_karakter(panel, FS_LABEL)
    for jdl, handles in kelompok:
        if not handles:
            continue
        for h in handles:
            h.set_label(textwrap.fill(" ".join(str(h.get_label()).split()), n))
        jdl = textwrap.fill(jdl, int(n * 0.86))
        lg = panel.legend(handles=handles, title=jdl, loc="upper left", bbox_to_anchor=(-0.02, y), frameon=False,
                          fontsize=FS_LABEL, title_fontsize=FS_KELOMPOK, alignment="left", borderaxespad=0,
                          borderpad=0.1, handlelength=1.5, handleheight=0.9, handletextpad=0.6, labelspacing=0.45)
        lg.get_title().set_fontweight("bold")
        lg.get_title().set_color(WARNA_TEKS)
        for t in lg.get_texts():
            t.set_color(WARNA_TEKS)
        panel.add_artist(lg)
        bb = lg.get_window_extent(renderer).transformed(panel.transAxes.inverted())
        y = bb.y0 - 0.045
    return y


def kolorbar(panel, cmap, vmin, vmax, judul_cb: str, y: float = 1.0, tinggi: float = 0.045):
    """Skala warna horizontal di bagian atas panel (data kontinu). Returns posisi bawah."""
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    panel.text(0.0, y, judul_cb, ha="left", va="top", fontsize=FS_KELOMPOK, fontweight="bold",
               color=WARNA_TEKS, transform=panel.transAxes)
    cax = panel.inset_axes([0.02, y - 0.09 - tinggi, 0.9, tinggi])
    cb = panel.figure.colorbar(ScalarMappable(Normalize(vmin, vmax), cmap), cax=cax, orientation="horizontal")
    cb.outline.set_linewidth(0.4)
    cb.ax.tick_params(labelsize=FS_LABEL - 0.5, length=2, width=0.4)
    cb.ax.xaxis.set_major_formatter(lambda v, _: angka(v, 1))
    return y - 0.09 - tinggi - 0.1


def arah_utara(panel, x: float, y: float, tinggi_in: float = 0.3):
    """Panah utara sederhana (segitiga + huruf U), berpangkal di (x, y) pecahan panel."""
    from matplotlib.patches import Polygon
    u = panel.figure._peta_ukuran
    th = tinggi_in / (u["h"] + u["tj"])                        # tinggi dalam pecahan panel
    lw = (tinggi_in * 0.42) / u["lebar_panel"]
    panel.add_patch(Polygon([(x - lw / 2, y), (x, y + th * 0.72), (x, y + th * 0.18)], closed=True,
                            facecolor=WARNA["batas_kab"], edgecolor=WARNA["batas_kab"], linewidth=0.4,
                            transform=panel.transAxes))
    panel.add_patch(Polygon([(x + lw / 2, y), (x, y + th * 0.72), (x, y + th * 0.18)], closed=True,
                            facecolor="white", edgecolor=WARNA["batas_kab"], linewidth=0.4,
                            transform=panel.transAxes))
    panel.text(x, y + th * 0.78, "U", ha="center", va="bottom", fontsize=FS_LABEL + 0.5, fontweight="bold",
               color=WARNA_TEKS, transform=panel.transAxes)


def skala(panel, ax_peta, x0: float, y: float, lebar_maks: float):
    """Skala batang dua segmen (0, setengah, penuh) dengan panjang 'bulat' sesuai skala peta. Returns L (m)."""
    from matplotlib.patches import Rectangle
    fig = panel.figure
    u = fig._peta_ukuran
    xl = ax_peta.get_xlim()
    m_per_inci = (xl[1] - xl[0]) / u["w"]
    L = panjang_skala(m_per_inci * lebar_maks * u["lebar_panel"])
    f = L / m_per_inci / u["lebar_panel"]
    h = 0.055 / (u["h"] + u["tj"])
    for i in range(2):
        panel.add_patch(Rectangle((x0 + i * f / 2, y), f / 2, h, facecolor=WARNA["batas_kab"] if i == 0 else "white",
                                  edgecolor=WARNA["batas_kab"], linewidth=0.4, transform=panel.transAxes))
    ty = y + h + 0.012
    for xv, t in ((x0, "0"), (x0 + f / 2, _label_jarak(L / 2, False)), (x0 + f, _label_jarak(L))):
        panel.text(xv, ty, t, ha="center", va="bottom", fontsize=FS_TEKNIS, color=WARNA_TEKS,
                   transform=panel.transAxes)
    return L


def blok_bawah(panel, ax_peta, sumber: str = ""):
    """Arah utara, skala batang, keterangan proyeksi dan sumber di dasar panel."""
    u = panel.figure._peta_ukuran
    tinggi = u["h"] + u["tj"]
    y_teks = 0.0
    baris = [KETERANGAN_PROYEKSI] + ([sumber] if sumber else [])
    teks = "\n".join(textwrap.fill(b, _lebar_karakter(panel, FS_TEKNIS) + 8) for b in baris)
    panel.text(0.0, y_teks, teks, ha="left", va="bottom", fontsize=FS_TEKNIS, color=WARNA_TEKS_2,
               transform=panel.transAxes, linespacing=1.35)
    n_baris = teks.count("\n") + 1
    y_elemen = (n_baris * FS_TEKNIS * 1.45 / 72 + 0.14) / tinggi
    arah_utara(panel, 0.07, y_elemen)
    skala(panel, ax_peta, 0.24, y_elemen + 0.02 / tinggi, 0.55)
    return y_elemen + 0.42 / tinggi                           # batas atas blok bawah


def periksa_ruang(y_legenda: float, y_blok: float, nama: str = ""):
    """Peringatan bila legenda menimpa blok bawah (tata letak harus disesuaikan, bukan dipotong diam-diam)."""
    if y_legenda < y_blok:
        import warnings
        warnings.warn(f"legenda menimpa blok arah utara/skala pada peta {nama}: {y_legenda:.3f} < {y_blok:.3f}")


def simpan(fig, path):
    """Simpan 300 dpi, ukuran figure tetap (tanpa pemangkasan otomatis agar seluruh peta sejenis berukuran sama)."""
    import matplotlib.pyplot as plt
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)

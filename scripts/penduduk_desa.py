"""Data penduduk per kalurahan (desa) Kulon Progo: tambahkan ke atribut KulonProgo_Desa.gpkg dan buat peta sebarannya.

    python -m scripts.penduduk_desa                  # tambah kolom ke GPKG lalu buat peta
    python -m scripts.penduduk_desa --hanya-peta     # buat peta dari kolom yang sudah ada

Sumber jumlah penduduk: data/Penduduk_Desa_KulonProgo.csv (kolom "Kalurahan/Village", "Penduduk"; 88 kalurahan).
Kolom yang ditambahkan ke layer KulonProgo_Desa:
  penduduk            jumlah penduduk (jiwa)
  luas_km2            luas poligon (km²) dihitung pada EPSG:32749 (UTM 49S)
  kepadatan_jiwa_km2  penduduk / luas_km2
Pencocokan memakai nama kalurahan (kolom NAMOBJ; tanpa awalan "Kelurahan", huruf besar/kecil dan spasi diabaikan).
Proses dihentikan bila ada kalurahan yang tidak cocok, supaya tidak ada nilai kosong diam-diam.

Peta (output_bab4/peta/): dua berkas terpisah, penduduk_desa_jumlah.png (jumlah penduduk) dan
penduduk_desa_kepadatan.png (kepadatan penduduk). Masing-masing choropleth 5 kelas kuantil (jumlah desa per kelas
± sama), dengan batas kapanewon, nomor peringkat 5 kalurahan tertinggi di peta, dan daftar namanya. Data ini hanya informasi
pendukung: tidak dipakai dalam analisis SDWFCM, TAS, maupun hasil terkunci. Data permukiman (bangunan/lahan
terbangun) tidak tersedia di repositori; peta permukiman memerlukan data tambahan.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA = PROJECT_ROOT / "data"
GPKG = DATA / "KulonProgo_Desa.gpkg"
KEC = DATA / "KulonProgo_Kec.gpkg"
CSV = DATA / "Penduduk_Desa_KulonProgo.csv"
PETA_DIR = PROJECT_ROOT / "output_bab4" / "peta"
N_LABEL = 5
CRS_UTM = "EPSG:32749"
KOLOM_NAMA = "NAMOBJ"
KOLOM_BARU = ["penduduk", "luas_km2", "kepadatan_jiwa_km2"]
N_KELAS = 5
# Ramp sekuensial satu hue, terang → gelap (panel 1 biru; panel 2 oranye = slot kategorikal berikutnya).
BIRU = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
ORANYE = ["#fde3d6", "#f8b89a", "#f28d63", "#eb6834", "#b8481d"]


def normalisasi_nama(s: str) -> str:
    """'Kelurahan Wates' → 'wates'; spasi ganda dan huruf besar/kecil diabaikan."""
    s = re.sub(r"^\s*(kelurahan|kalurahan|desa)\s+", "", str(s), flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def gabung_penduduk(desa, penduduk: pd.DataFrame, kolom_nama: str = KOLOM_NAMA,
                    kolom_csv: str = "Kalurahan/Village", kolom_nilai: str = "Penduduk"):
    """GeoDataFrame desa + kolom penduduk, luas_km2, kepadatan_jiwa_km2. Error bila ada nama yang tidak cocok
    atau ganda."""
    p = penduduk.assign(_kunci=penduduk[kolom_csv].map(normalisasi_nama))
    if p["_kunci"].duplicated().any():
        raise ValueError(f"Nama ganda di data penduduk: {sorted(p.loc[p['_kunci'].duplicated(), kolom_csv])}")
    kunci = desa[kolom_nama].map(normalisasi_nama)
    if kunci.duplicated().any():
        raise ValueError(f"Nama ganda di {kolom_nama}: {sorted(desa.loc[kunci.duplicated(), kolom_nama])}")
    hilang_csv = sorted(set(kunci) - set(p["_kunci"]))
    hilang_gpkg = sorted(set(p["_kunci"]) - set(kunci))
    if hilang_csv or hilang_gpkg:
        raise ValueError(f"Nama tidak cocok. Tidak ada di data penduduk: {hilang_csv}; tidak ada di peta: {hilang_gpkg}")
    out = desa.drop(columns=[c for c in KOLOM_BARU if c in desa.columns]).copy()
    out["penduduk"] = kunci.map(p.set_index("_kunci")[kolom_nilai]).astype("int64").values
    out["luas_km2"] = out.geometry.to_crs(CRS_UTM).area.values / 1e6
    out["kepadatan_jiwa_km2"] = out["penduduk"] / out["luas_km2"]
    return out


def tambah_ke_gpkg(gpkg: Path = GPKG, csv: Path = CSV):
    """Tulis kolom penduduk ke layer GPKG (layer, CRS, dan kolom lain dipertahankan)."""
    import geopandas as gpd
    import pyogrio
    layer = pyogrio.list_layers(gpkg)[0][0]
    desa = gpd.read_file(gpkg, layer=layer)
    hasil = gabung_penduduk(desa, pd.read_csv(csv))
    hasil.to_file(gpkg, layer=layer, driver="GPKG")
    return hasil


def kelas_kuantil(v: np.ndarray, n: int = N_KELAS) -> np.ndarray:
    """Batas kelas kuantil (n + 1 nilai, termasuk minimum dan maksimum)."""
    return np.quantile(np.asarray(v, float), np.linspace(0, 1, n + 1))


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


PANEL = {"jumlah": ("penduduk", "Jumlah penduduk (jiwa)", BIRU),
         "kepadatan": ("kepadatan_jiwa_km2", "Kepadatan penduduk (jiwa/km²)", ORANYE)}


def peta_sebaran_penduduk(gpkg: Path = GPKG, out_dir: Path = PETA_DIR, kec: Path = KEC) -> list:
    """Dua peta choropleth terpisah per kalurahan (5 kelas kuantil, label 5 kalurahan tertinggi):
    penduduk_desa_jumlah.png dan penduduk_desa_kepadatan.png. Returns daftar berkas."""
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    desa = gpd.read_file(gpkg).to_crs(CRS_UTM)
    if not set(KOLOM_BARU) <= set(desa.columns):
        raise ValueError("Kolom penduduk belum ada; jalankan tambah_ke_gpkg terlebih dahulu.")
    batas_kec = gpd.read_file(kec).to_crs(CRS_UTM) if Path(kec).exists() else None
    tot = int(desa["penduduk"].sum())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for nama, (kol, judul, ramp) in PANEL.items():
        v = desa[kol].values
        b = kelas_kuantil(v)
        k = np.clip(np.searchsorted(b, v, side="right") - 1, 0, N_KELAS - 1)
        fig, ax = plt.subplots(figsize=(7.2, 8.4), dpi=150)
        desa.plot(ax=ax, color=np.array(ramp)[k], edgecolor="white", linewidth=0.5)
        if batas_kec is not None:
            batas_kec.boundary.plot(ax=ax, color="#3f3f46", linewidth=0.7)
        top = desa.nlargest(N_LABEL, kol)
        daftar = []
        for rank, (_, r) in enumerate(top.iterrows(), start=1):   # penanda nomor (tidak bertumpuk) + daftar
            p = r.geometry.representative_point()
            ax.annotate(str(rank), (p.x, p.y), fontsize=6.5, fontweight="bold", color="#18181b", ha="center",
                        va="center", bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="#18181b", lw=0.6))
            daftar.append(f"{rank}. {r[KOLOM_NAMA]}: {_fmt(r[kol])}")
        ax.text(0.01, 0.99, "\n".join([f"{N_LABEL} kalurahan tertinggi"] + daftar), transform=ax.transAxes,
                ha="left", va="top", fontsize=7, color="#18181b", linespacing=1.4,
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#a1a1aa", lw=0.5, alpha=0.95))
        n_kelas = np.bincount(k, minlength=N_KELAS)
        ax.legend(handles=[Patch(facecolor=ramp[i], edgecolor="#a1a1aa", linewidth=0.4,
                                 label=f"{_fmt(b[i])} – {_fmt(b[i + 1])}  ({n_kelas[i]} desa)")
                           for i in range(N_KELAS)],
                  title=judul, loc="lower left", fontsize=7, title_fontsize=7.5, frameon=True, framealpha=0.9)
        ax.set_title(f"{judul} per kalurahan, Kabupaten Kulon Progo\n(total {_fmt(tot)} jiwa, {len(desa)} kalurahan)",
                     fontsize=10, color="#18181b")
        ax.set_axis_off()
        fig.text(0.5, 0.012, "Kelas kuantil (jumlah desa per kelas ± sama). Garis gelap = batas kapanewon; nomor = peringkat "
                 f"{N_LABEL} kalurahan tertinggi."
                 + ("\nKepadatan = penduduk / luas poligon (EPSG:32749)." if nama == "kepadatan" else ""),
                 ha="center", va="bottom", fontsize=6.5, color="#52525b")
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        f = out_dir / f"penduduk_desa_{nama}.png"
        fig.savefig(f)
        plt.close(fig)
        files.append(f)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description="Penduduk per kalurahan: tambah ke GPKG dan buat peta sebaran")
    ap.add_argument("--hanya-peta", action="store_true")
    args = ap.parse_args(argv)
    if not args.hanya_peta:
        h = tambah_ke_gpkg()
        print(f"{len(h)} kalurahan; total penduduk {_fmt(h['penduduk'].sum())} jiwa; kolom ditambahkan: {KOLOM_BARU}")
    for f in peta_sebaran_penduduk():
        print(f"peta: {f}")


if __name__ == "__main__":
    sys.exit(main())

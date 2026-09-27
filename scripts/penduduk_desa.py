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

Peta (output_bab4/peta/sebaran_penduduk_desa.png): dua panel choropleth, jumlah penduduk dan kepadatan penduduk,
masing-masing 5 kelas kuantil (jumlah desa per kelas ± sama), dengan batas kapanewon. Data ini hanya informasi
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
PETA = PROJECT_ROOT / "output_bab4" / "peta" / "sebaran_penduduk_desa.png"
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


def peta_sebaran_penduduk(gpkg: Path = GPKG, out_png: Path = PETA, kec: Path = KEC) -> Path:
    """Peta choropleth dua panel: jumlah penduduk dan kepadatan penduduk per kalurahan (5 kelas kuantil)."""
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    desa = gpd.read_file(gpkg).to_crs(CRS_UTM)
    if not set(KOLOM_BARU) <= set(desa.columns):
        raise ValueError("Kolom penduduk belum ada; jalankan tambah_ke_gpkg terlebih dahulu.")
    batas_kec = gpd.read_file(kec).to_crs(CRS_UTM) if Path(kec).exists() else None
    panel = [("penduduk", "Jumlah penduduk (jiwa)", BIRU),
             ("kepadatan_jiwa_km2", "Kepadatan penduduk (jiwa/km²)", ORANYE)]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 7.8), dpi=150)
    for ax, (kol, judul, ramp) in zip(axes, panel):
        v = desa[kol].values
        b = kelas_kuantil(v)
        k = np.clip(np.searchsorted(b, v, side="right") - 1, 0, N_KELAS - 1)
        desa.plot(ax=ax, color=np.array(ramp)[k], edgecolor="white", linewidth=0.5)
        if batas_kec is not None:
            batas_kec.boundary.plot(ax=ax, color="#3f3f46", linewidth=0.7)
        for _, r in desa.nlargest(3, kol).iterrows():          # label selektif: 3 desa tertinggi
            p = r.geometry.representative_point()
            ax.annotate(r[KOLOM_NAMA], (p.x, p.y), fontsize=6.5, color="#18181b", ha="center",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
        n_kelas = np.bincount(k, minlength=N_KELAS)
        ax.legend(handles=[Patch(facecolor=ramp[i], edgecolor="#a1a1aa", linewidth=0.4,
                                 label=f"{_fmt(b[i])} – {_fmt(b[i + 1])}  ({n_kelas[i]} desa)")
                           for i in range(N_KELAS)],
                  title=judul, loc="lower left", fontsize=7, title_fontsize=7.5, frameon=True, framealpha=0.9)
        ax.set_title(judul, fontsize=10, color="#18181b")
        ax.set_axis_off()
    tot = int(desa["penduduk"].sum())
    fig.suptitle(f"Sebaran penduduk per kalurahan, Kabupaten Kulon Progo (total {_fmt(tot)} jiwa, {len(desa)} kalurahan)",
                 fontsize=11, color="#18181b")
    fig.text(0.5, 0.02, "Kelas kuantil (jumlah desa per kelas ± sama). Garis gelap = batas kapanewon; label = 3 kalurahan "
             "dengan nilai tertinggi. Kepadatan = penduduk / luas poligon (EPSG:32749).", ha="center", fontsize=7,
             color="#52525b")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    return Path(out_png)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Penduduk per kalurahan: tambah ke GPKG dan buat peta sebaran")
    ap.add_argument("--hanya-peta", action="store_true")
    args = ap.parse_args(argv)
    if not args.hanya_peta:
        h = tambah_ke_gpkg()
        print(f"{len(h)} kalurahan; total penduduk {_fmt(h['penduduk'].sum())} jiwa; kolom ditambahkan: {KOLOM_BARU}")
    print(f"peta: {peta_sebaran_penduduk()}")


if __name__ == "__main__":
    sys.exit(main())

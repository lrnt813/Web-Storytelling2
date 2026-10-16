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
± sama), dengan batas kapanewon dan kabupaten, arah utara, skala, nomor peringkat 5 kalurahan tertinggi di peta, dan daftar namanya. Data ini hanya informasi
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


# Warna kelas: scripts/peta_util.PENDUDUK (gradasi satu warna terang → gelap; biru tidak dipakai karena khusus genangan)
PANEL = {"jumlah": ("penduduk", "Jumlah penduduk", "jiwa"),
         "kepadatan": ("kepadatan_jiwa_km2", "Kepadatan penduduk", "jiwa/km²")}


def peta_sebaran_penduduk(gpkg: Path = GPKG, out_dir: Path = PETA_DIR, kec: Path = KEC) -> list:
    """Dua peta choropleth terpisah per kalurahan (5 kelas kuantil, nomor 5 kalurahan tertinggi):
    penduduk_desa_jumlah.png dan penduduk_desa_kepadatan.png, dengan tata letak scripts/peta_util.py (sama dengan
    peta kabupaten Bab IV). Returns daftar berkas."""
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    from scripts import peta_util as PU
    desa = gpd.read_file(gpkg).to_crs(CRS_UTM)
    if not set(KOLOM_BARU) <= set(desa.columns):
        raise ValueError("Kolom penduduk belum ada; jalankan tambah_ke_gpkg terlebih dahulu.")
    tot = int(desa["penduduk"].sum())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = desa.total_bounds
    pad = 900.0
    rasio = (y1 - y0 + 2 * pad) / (x1 - x0 + 2 * pad)
    batas = PU.sesuaikan_rasio(x0 - pad, x1 + pad, y0 - pad, y1 + pad, rasio, rasio)
    files = []
    for nama, (kol, judul, satuan) in PANEL.items():
        ramp = PU.PENDUDUK[nama]
        v = desa[kol].values
        b = kelas_kuantil(v)
        k = np.clip(np.searchsorted(b, v, side="right") - 1, 0, N_KELAS - 1)
        fig, (ax,), panel = PU.kanvas(1, rasio)
        desa.plot(ax=ax, color=np.array(ramp)[k], edgecolor="white", linewidth=0.3, zorder=1)
        if Path(kec).exists():
            gpd.read_file(kec).to_crs(CRS_UTM).boundary.plot(ax=ax, color=PU.WARNA["batas_kec"],
                                                             linewidth=PU.LEBAR_BATAS_KEC, zorder=5)
        b_kab = desa.dissolve().boundary
        b_kab.plot(ax=ax, color=PU.WARNA["batas_kab"], linewidth=PU.LEBAR_BATAS_KAB, zorder=6)
        top = desa.nlargest(N_LABEL, kol)
        peringkat = []
        for rank, (_, r) in enumerate(top.iterrows(), start=1):   # nomor peringkat di peta + daftar di legenda
            p = r.geometry.representative_point()
            ax.annotate(str(rank), (p.x, p.y), fontsize=PU.FS_TEKNIS, fontweight="bold", color=PU.WARNA_TEKS,
                        ha="center", va="center", zorder=8,
                        bbox=dict(boxstyle="circle,pad=0.22", fc="white", ec=PU.WARNA_TEKS, lw=0.5))
            peringkat.append(PU.titik(PU.WARNA_TEKS, f"{r[KOLOM_NAMA]} — {_fmt(r[kol])}", penanda=f"${rank}$",
                                      ukuran=6))
        PU.atur_batas(ax, *batas)
        n_kelas = np.bincount(k, minlength=N_KELAS)
        kelas = [PU.kotak(ramp[i], f"{_fmt(b[i])} – {_fmt(b[i + 1])} ({n_kelas[i]} kalurahan)") for i in range(N_KELAS)]
        PU.judul(fig, f"{judul} per kalurahan",
                 f"Kabupaten Kulon Progo · total {_fmt(tot)} jiwa, {len(desa)} kalurahan · 5 kelas kuantil "
                 "(jumlah kalurahan per kelas ± sama)"
                 + (" · kepadatan = penduduk / luas poligon kalurahan" if nama == "kepadatan" else ""))
        y_blok = PU.blok_bawah(panel, ax, "Sumber: data penduduk per kalurahan; batas administrasi BIG, skala "
                                          "1:10.000")
        y = PU.legenda(panel, [(f"{judul} ({satuan})", kelas),
                               (f"{N_LABEL} kalurahan tertinggi", peringkat),
                               ("Referensi", [PU.handle_batas_kec(), PU.handle_batas_kab()])])
        PU.periksa_ruang(y, y_blok, f"penduduk_desa_{nama}")
        f = out_dir / f"penduduk_desa_{nama}.png"
        PU.simpan(fig, f)
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

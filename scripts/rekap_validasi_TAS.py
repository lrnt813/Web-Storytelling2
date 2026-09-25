"""Rekap lembar validasi manual TAS v6 yang sudah diisi peneliti.

    python -m scripts.rekap_validasi_TAS                       # output_bab4/validasi/validasi_TAS_v6.xlsx
    python -m scripts.rekap_validasi_TAS --lembar BERKAS.xlsx

Keluaran (output_bab4/validasi/):
  rekap_validasi_TAS.xlsx  lembar: per level × Kode utama (jumlah dan %), per level × Valid, Atribusi banjir ×
                           Kode utama (Rendah/Sedang/Tinggi), per hotspot, dan tabel ringkas Bab IV
  rekap_validasi_TAS.md    tabel yang sama dalam format Markdown

Kolom "Valid" dihitung ulang dari Kode utama (A/B/C/D/G → Y; E/F/H → T; I → cek), sehingga rekap tidak
bergantung pada nilai rumus yang tersimpan di lembar. Skrip ini hanya membaca lembar validasi; tidak
menjalankan analisis dan tidak mengubah hasil terkunci.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDASI_DIR = PROJECT_ROOT / "output_bab4" / "validasi"
LEMBAR = VALIDASI_DIR / "validasi_TAS_v6.xlsx"
SHEET = "Validasi TAS"
SHEET_HOTSPOT = "Hotspot"
LEVEL_ORDER = ["Baseline", "Rendah", "Sedang", "Tinggi"]
BELUM = "(belum diisi)"

KODE = {
    "A": "Sungai/waduk",
    "B": "Kawasan tertutup/bandara",
    "C": "Topografi perbukitan",
    "D": "Jaringan jalan memang jarang",
    "E": "Jaringan OSM tidak lengkap",
    "F": "Kesalahan snapping",
    "G": "Penutupan ruas akibat banjir",
    "H": "TES lebih dekat tidak tercatat",
    "I": "Belum terjelaskan",
}
KODE_PILIHAN = [f"{k} {v}" for k, v in KODE.items()]     # isi dropdown
VALID_DARI_KODE = {**{k: "Y" for k in "ABCDG"}, **{k: "T" for k in "EFH"}, "I": "cek"}
STATUS_ISIAN = ["otomatis", "perlu konfirmasi peneliti", "perlu divalidasi"]
ATRIBUSI = ["dipicu banjir", "diperparah banjir", "tidak berubah", "lainnya"]
KELOMPOK_BAB4 = {"TAS struktural (A/B/C/D)": "ABCD", "TAS akibat banjir (G)": "G",
                 "Artefak data/metode (E/F/H)": "EFH", "Belum terjelaskan (I)": "I"}


def kode_huruf(v) -> str:
    """Huruf kode dari isian dropdown ("A Sungai/waduk" → "A"); kosong/tidak dikenal → ""."""
    s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
    return s[:1].upper() if s[:1].upper() in KODE and (len(s) == 1 or s[1] in " -.") else ""


def valid_dari_kode(v) -> str:
    return VALID_DARI_KODE.get(kode_huruf(v), "")


def _pct(t: pd.DataFrame) -> pd.DataFrame:
    tot = t.sum(axis=1).replace(0, float("nan"))
    return (t.div(tot, axis=0) * 100).round(1)


def rekap(df: pd.DataFrame, hotspot: pd.DataFrame = None) -> dict:
    """Tabel rekap dari lembar validasi v6 (DataFrame lembar "Validasi TAS"; opsional lembar "Hotspot")."""
    d = df.copy()
    d["kode"] = d["Kode utama"].map(kode_huruf).replace("", BELUM)
    d["valid"] = d["Kode utama"].map(valid_dari_kode).replace("", BELUM)
    levels = [lv for lv in LEVEL_ORDER if lv in set(d["level"])]
    kode_cols = list(KODE) + [BELUM]
    per_kode = pd.crosstab(d["level"], d["kode"]).reindex(index=levels, columns=kode_cols, fill_value=0)
    per_kode_pct = _pct(per_kode)
    per_kode["Total"] = per_kode.sum(axis=1)
    valid = pd.crosstab(d["level"], d["valid"]).reindex(index=levels, columns=["Y", "T", "cek", BELUM], fill_value=0)
    valid["Total"] = valid.sum(axis=1)

    f = d[d["level"] != "Baseline"].copy()
    f["Atribusi banjir"] = f["Atribusi banjir"].fillna("").astype(str).replace("", BELUM)
    idx = pd.MultiIndex.from_product([[lv for lv in levels if lv != "Baseline"], ATRIBUSI + [BELUM]],
                                     names=["level", "atribusi"])
    atr = (f.groupby(["level", "Atribusi banjir", "kode"]).size().unstack("kode")
           .reindex(index=idx, columns=kode_cols, fill_value=0).fillna(0).astype(int))
    atr = atr[atr.sum(axis=1) > 0]

    bab4 = pd.DataFrame(index=levels)
    for name, letters in KELOMPOK_BAB4.items():
        bab4[name] = [int(d.loc[d["level"] == lv, "kode"].isin(list(letters)).sum()) for lv in levels]
    bab4[BELUM] = [int((d.loc[d["level"] == lv, "kode"] == BELUM).sum()) for lv in levels]
    bab4["Total TAS"] = bab4.sum(axis=1)

    out = {"per_kode": per_kode, "per_kode_persen": per_kode_pct, "valid": valid, "atribusi_x_kode": atr,
           "bab4": bab4}
    if "Hotspot" in d.columns:
        h = d[d["Hotspot"].notna() & (d["Hotspot"].astype(str).str.strip() != "")]
        per_h = h.groupby("Hotspot").agg(baris=("id_grid", "size"), grid_unik=("id_grid", "nunique"),
                                         level=("level", lambda s: ", ".join(lv for lv in LEVEL_ORDER if lv in set(s))))
        per_h = per_h.join(pd.crosstab(h["Hotspot"], h["kode"]).reindex(columns=kode_cols, fill_value=0))
        if hotspot is not None and len(hotspot):
            hs = hotspot.set_index("Hotspot")[["Kode utama", "Kode tambahan"]]
            per_h = per_h.join(hs.rename(columns={"Kode utama": "Kode utama hotspot",
                                                  "Kode tambahan": "Kode tambahan hotspot"}))
        out["hotspot"] = per_h
    return out


def to_md(df: pd.DataFrame) -> str:
    """Tabel Markdown sederhana (tanpa ketergantungan tambahan)."""
    names = [n or "" for n in (df.index.names if df.index.nlevels > 1 else [df.index.name or ""])]
    head = [" / ".join(names) or "baris"] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for idx, row in df.iterrows():
        lab = " / ".join(map(str, idx)) if isinstance(idx, tuple) else str(idx)
        lines.append("| " + " | ".join([lab] + ["" if pd.isna(v) else str(v) for v in row.values]) + " |")
    return "\n".join(lines)


JUDUL = {"per_kode": "Kode utama per level (jumlah baris)", "per_kode_persen": "Kode utama per level (%)",
         "valid": "Valid per level (dari Kode utama)", "atribusi_x_kode": "Atribusi banjir × Kode utama",
         "hotspot": "Per hotspot", "bab4": "Tabel ringkas Bab IV"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rekap lembar validasi manual TAS v6")
    ap.add_argument("--lembar", type=Path, default=LEMBAR)
    ap.add_argument("--keluaran", type=Path, default=VALIDASI_DIR)
    args = ap.parse_args(argv)
    df = pd.read_excel(args.lembar, sheet_name=SHEET)
    try:
        hs = pd.read_excel(args.lembar, sheet_name=SHEET_HOTSPOT)
    except ValueError:
        hs = None
    r = rekap(df, hs)
    args.keluaran.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.keluaran / "rekap_validasi_TAS.xlsx") as xw:
        for k, t in r.items():
            t.to_excel(xw, sheet_name=k[:31])
    L = ["# Rekap validasi manual TAS v6", "", f"Sumber: `{args.lembar.name}`. Valid dihitung dari Kode utama "
         "(A/B/C/D/G → Y; E/F/H → T; I → cek).", ""]
    for k, t in r.items():
        L += [f"## {JUDUL[k]}", "", to_md(t), ""]
    (args.keluaran / "rekap_validasi_TAS.md").write_text("\n".join(L), encoding="utf-8")
    print(r["bab4"])


if __name__ == "__main__":
    sys.exit(main())

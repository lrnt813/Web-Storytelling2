"""Rekap lembar validasi manual TAS yang sudah diisi peneliti.

    python -m scripts.rekap_validasi_TAS                       # output_bab4/validasi/validasi_TAS.xlsx
    python -m scripts.rekap_validasi_TAS --lembar BERKAS.xlsx

Keluaran (output_bab4/validasi/):
  rekap_validasi_TAS.csv   jumlah grid TAS per level × penyebab, dan per level × Valid (Y/T)
  rekap_validasi_TAS.md    tabel yang sama dalam format Markdown

Skrip ini hanya membaca lembar validasi; tidak menjalankan analisis dan tidak mengubah hasil terkunci.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDASI_DIR = PROJECT_ROOT / "output_bab4" / "validasi"
LEMBAR = VALIDASI_DIR / "validasi_TAS.xlsx"
SHEET = "Validasi TAS"
PENYEBAB = ["sungai tanpa jembatan", "rel", "lereng-perbukitan", "jalan buntu", "data OSM tidak lengkap", "lainnya"]
LEVEL_ORDER = ["Baseline", "Rendah", "Sedang", "Tinggi"]
BELUM = "(belum diisi)"


def rekap(df: pd.DataFrame) -> dict:
    """Tabel jumlah grid per level × penyebab dan per level × Valid (Y/T). Nilai di luar pilihan
    dikelompokkan sebagai 'lainnya'; sel kosong sebagai '(belum diisi)'."""
    d = df.copy()
    d["Penyebab"] = d["Penyebab"].fillna("").astype(str).str.strip()
    d.loc[d["Penyebab"] == "", "Penyebab"] = BELUM
    d.loc[~d["Penyebab"].isin(PENYEBAB + [BELUM]), "Penyebab"] = "lainnya"
    d["Valid (Y/T)"] = d["Valid (Y/T)"].fillna("").astype(str).str.strip().str.upper().replace({"": BELUM})
    levels = [lv for lv in LEVEL_ORDER if lv in set(d["level"])]
    cause = (pd.crosstab(d["level"], d["Penyebab"]).reindex(index=levels, columns=PENYEBAB + [BELUM], fill_value=0))
    cause["Total"] = cause.sum(axis=1)
    valid = (pd.crosstab(d["level"], d["Valid (Y/T)"]).reindex(index=levels, columns=["Y", "T", BELUM], fill_value=0))
    return {"penyebab": cause, "valid": valid}


def to_md(df: pd.DataFrame) -> str:
    """Tabel Markdown sederhana (tanpa ketergantungan tambahan)."""
    head = ["level"] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [str(v) for v in row.values]) + " |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rekap lembar validasi manual TAS")
    ap.add_argument("--lembar", type=Path, default=LEMBAR)
    args = ap.parse_args(argv)
    df = pd.read_excel(args.lembar, sheet_name=SHEET)
    r = rekap(df)
    VALIDASI_DIR.mkdir(parents=True, exist_ok=True)
    out = pd.concat({"Penyebab": r["penyebab"], "Valid": r["valid"]}, axis=1)
    out.to_csv(VALIDASI_DIR / "rekap_validasi_TAS.csv", encoding="utf-8-sig")
    L = ["# Rekap validasi manual TAS", "", f"Sumber: `{args.lembar.name}`.", "", "## Penyebab per level", "",
         to_md(r["penyebab"]), "", "## Valid (Y/T) per level", "", to_md(r["valid"]), ""]
    (VALIDASI_DIR / "rekap_validasi_TAS.md").write_text("\n".join(L), encoding="utf-8")
    print(r["penyebab"])
    print(r["valid"])


if __name__ == "__main__":
    sys.exit(main())

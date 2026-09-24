"""Putaran 5: rekap lembar validasi TAS dan catatan algoritma."""
import pandas as pd

from scripts.export_bab4 import algo_note
from scripts.rekap_validasi_TAS import BELUM, PENYEBAB, rekap


def test_rekap_penyebab_dan_valid():
    df = pd.DataFrame({
        "level": ["Baseline", "Baseline", "Sedang", "Sedang", "Tinggi"],
        "Penyebab": ["rel", None, "jalan buntu", "sesuatu lain", "rel"],
        "Valid (Y/T)": ["y", None, "T", "Y", "Y"],
    })
    r = rekap(df)
    c, v = r["penyebab"], r["valid"]
    assert list(c.index) == ["Baseline", "Sedang", "Tinggi"]
    assert c.loc["Baseline", "rel"] == 1 and c.loc["Baseline", BELUM] == 1 and c.loc["Baseline", "Total"] == 2
    assert c.loc["Sedang", "lainnya"] == 1 and c.loc["Sedang", "jalan buntu"] == 1
    assert v.loc["Baseline", "Y"] == 1 and v.loc["Sedang", "T"] == 1 and v.loc["Baseline", BELUM] == 1
    assert list(c.columns[:len(PENYEBAB)]) == PENYEBAB


def test_catatan_algoritma():
    assert algo_note({"status": "ok", "klaster_terbesar_persen": 89.35}) == "nyaris degeneratif (klaster terbesar 89,3%; batas 90%)"
    assert algo_note({"status": "ok", "klaster_terbesar_persen": 40.0}) == ""
    assert algo_note({"status": "degeneratif", "klaster_terbesar_persen": 98.2}).startswith("degeneratif")
    assert algo_note({"status": "gagal"}).startswith("gagal")


def test_rekap_markdown_tanpa_tabulate():
    from scripts.rekap_validasi_TAS import to_md
    df = pd.DataFrame({"level": ["Baseline"], "Penyebab": ["rel"], "Valid (Y/T)": ["Y"]})
    md = to_md(rekap(df)["penyebab"])
    assert md.splitlines()[0].startswith("| level | sungai tanpa jembatan")

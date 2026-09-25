"""Rekap lembar validasi TAS v6 (Putaran 6) dan catatan algoritma (Putaran 5)."""
import pandas as pd

from scripts.export_bab4 import algo_note
from scripts.rekap_validasi_TAS import BELUM, KODE_PILIHAN, kode_huruf, rekap, valid_dari_kode


def _lembar_contoh():
    return pd.DataFrame({
        "id_grid": [1, 2, 3, 1, 4, 5, 6],
        "level": ["Baseline", "Baseline", "Baseline", "Sedang", "Sedang", "Sedang", "Tinggi"],
        "Hotspot": ["H01", "H01", None, "H01", "H02", "H02", None],
        "Atribusi banjir": [None, None, None, "diperparah banjir", "dipicu banjir", "lainnya", "dipicu banjir"],
        "Kode utama": ["A Sungai/waduk", "F Kesalahan snapping", None, "A Sungai/waduk", "G Penutupan ruas akibat banjir",
                       "I Belum terjelaskan", "G"],
        "Kode tambahan": [None, None, None, "G Penutupan ruas akibat banjir", "E Jaringan OSM tidak lengkap", None, None],
    })


def test_kode_dan_valid():
    assert kode_huruf("A Sungai/waduk") == "A" and kode_huruf("g") == "G" and kode_huruf(None) == ""
    assert kode_huruf("Apa saja") == "" and kode_huruf(float("nan")) == ""
    assert [valid_dari_kode(k) for k in ("B x", "G", "E", "F", "H", "I", "")] == ["Y", "Y", "T", "T", "T", "cek", ""]
    assert len(KODE_PILIHAN) == 9 and KODE_PILIHAN[5] == "F Kesalahan snapping"


def test_rekap_v6():
    r = rekap(_lembar_contoh(), pd.DataFrame({"Hotspot": ["H01", "H02"], "Kode utama": ["A Sungai/waduk", None],
                                              "Kode tambahan": [None, None]}))
    k = r["per_kode"]
    assert list(k.index) == ["Baseline", "Sedang", "Tinggi"]
    assert k.loc["Baseline", "A"] == 1 and k.loc["Baseline", "F"] == 1 and k.loc["Baseline", BELUM] == 1
    assert k.loc["Sedang", "Total"] == 3 and k.loc["Tinggi", "G"] == 1
    assert r["per_kode_persen"].loc["Sedang", "G"] == 33.3
    v = r["valid"]
    assert v.loc["Baseline", "Y"] == 1 and v.loc["Baseline", "T"] == 1 and v.loc["Sedang", "cek"] == 1
    a = r["atribusi_x_kode"]
    assert a.loc[("Sedang", "dipicu banjir"), "G"] == 1 and a.loc[("Sedang", "diperparah banjir"), "A"] == 1
    assert "Baseline" not in a.index.get_level_values(0)
    b = r["bab4"]
    assert b.loc["Baseline", "TAS struktural (A/B/C/D)"] == 1 and b.loc["Baseline", "Artefak data/metode (E/F/H)"] == 1
    assert b.loc["Sedang", "TAS akibat banjir (G)"] == 1 and b.loc["Sedang", "Belum terjelaskan (I)"] == 1
    assert (b["Total TAS"] == k["Total"]).all()
    h = r["hotspot"]
    assert h.loc["H01", "baris"] == 3 and h.loc["H01", "grid_unik"] == 2 and h.loc["H01", "level"] == "Baseline, Sedang"
    assert h.loc["H01", "Kode utama hotspot"] == "A Sungai/waduk"


def test_rekap_main_menulis_berkas(tmp_path):
    from scripts.rekap_validasi_TAS import main
    f = tmp_path / "lembar.xlsx"
    with pd.ExcelWriter(f) as xw:
        _lembar_contoh().to_excel(xw, sheet_name="Validasi TAS", index=False)
    main(["--lembar", str(f), "--keluaran", str(tmp_path)])
    assert (tmp_path / "rekap_validasi_TAS.xlsx").exists()
    md = (tmp_path / "rekap_validasi_TAS.md").read_text(encoding="utf-8")
    assert "Tabel ringkas Bab IV" in md and "TAS struktural (A/B/C/D)" in md


def test_catatan_algoritma():
    assert algo_note({"status": "ok", "klaster_terbesar_persen": 89.35}) == "nyaris degeneratif (klaster terbesar 89,3%; batas 90%)"
    assert algo_note({"status": "ok", "klaster_terbesar_persen": 40.0}) == ""
    assert algo_note({"status": "degeneratif", "klaster_terbesar_persen": 98.2}).startswith("degeneratif")
    assert algo_note({"status": "gagal"}).startswith("gagal")


def test_rekap_markdown_tanpa_tabulate():
    from scripts.rekap_validasi_TAS import to_md
    md = to_md(rekap(_lembar_contoh())["bab4"])
    assert md.splitlines()[0].startswith("| baris | TAS struktural")

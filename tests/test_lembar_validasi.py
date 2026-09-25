"""Putaran 6: isian awal otomatis lembar validasi TAS v6 (aturan kata kunci, prioritas (a)–(e), hotspot)."""
import numpy as np
import pandas as pd

from scripts.lembar_validasi_TAS import add_hotspots, kode_dari_teks, pilihan, prefill

UMUM = ("Opsi jalan yang disediakan oleh OSM terbatas dibandingkan Google Maps, ditambah terdapat ruas jalan "
        "yang tidak dapat dilewati akibat terdampak bencana banjir")


def test_kata_kunci_berurutan():
    assert kode_dari_teks("Memang jalan memutar karena grid dan TES terpisah oleh sungai serang dan rute yang "
                          "dilalui sudah melewati jembatan terdekat") == ["A"]
    assert kode_dari_teks("Memang jalan memutar karena grid berada di kawasan bandara internasional") == ["B"]
    assert kode_dari_teks("Berada di kawasan bandara internasional. Namun ... keterbatasan OSM") == ["E"]
    assert kode_dari_teks("Seharusnya tidak perlu memutar ... Pasti ada kesalahan") == ["I"]
    assert kode_dari_teks("Terdapat kesalahan pada snapping. Lalu keterbatasan jaringan OSM dibandingkan Google Maps") == ["F", "E"]
    assert kode_dari_teks("lembah perbukitan menoreh, kontur; keterbatasan OSM") == ["C", "E"]
    assert kode_dari_teks("Daerah pesisir ... jaringan jalan OSM") == ["D", "E"]
    assert kode_dari_teks("TES yang lebih dekat kemungkinan tidak ikut terscraping. keterbatasan OSM") == ["H", "E"]
    assert kode_dari_teks("sungai tanpa kata penghubung") == [] and kode_dari_teks(None) == []


def _v6():
    return pd.DataFrame({
        "id_grid": [1, 2, 3, 4, 5, 1, 1, 6, 2, 7, 1],
        "level": ["Baseline", "Baseline", "Baseline", "Baseline", "Baseline", "Rendah", "Sedang", "Sedang", "Sedang",
                  "Tinggi", "Tinggi"],
        "Lat TES": [-7.0] * 11, "Lon TES": [110.0] * 11,
        "T_aktual (menit)": [40.0, 50.0, 60.5, 45.0, 70.0, 40.5, 55.0, 35.0, 50.2, 33.0, 38.0],
        "Atribusi banjir": [None] * 5 + ["tidak berubah", "diperparah banjir", "dipicu banjir", "tidak berubah",
                                         "lainnya", "diperparah banjir"],
    })


def _v5():
    return pd.DataFrame({
        "id_grid": [1, 2, 3, 4, 1, 1],
        "level": ["Baseline", "Baseline", "Baseline", "Baseline", "Rendah", "Sedang"],
        "Lat TES": [-7.0, -7.0, -7.0, -7.1, -7.0, -7.0], "Lon TES": [110.0] * 6,
        "T_aktual (menit)": [40.4, 49.5, 60.0, 45.0, 40.0, 50.0],
        "Penyebab": ["Memang jalan memutar karena grid dan TES terpisah oleh sungai serang dan rute sudah melewati "
                     "jembatan terdekat", None, "Keterbatasan jaringan OSM dibandingkan dengan google maps", "x",
                     "Berada di lembah perbukitan", UMUM],
        "Catatan": [None, "Terdapat kesalahan pada snapping. Snapping tidak memilih ruas terdekat", None, None,
                    "catatan rendah", None],
    })


def test_prefill_prioritas():
    p = prefill(_v6(), _v5())
    g = lambda i, c: p.at[i, c]
    # (a) grid 1 Baseline: TES sama, |ΔT| 0,4 ≤ 1 → teks dibawa, kode A, perlu konfirmasi
    assert g(0, "Kode utama") == pilihan("A") and g(0, "Kode tambahan") == ""
    assert g(0, "Status isian") == "perlu konfirmasi peneliti" and g(0, "Penyebab (teks)").startswith("Memang")
    # (a) pengecualian F: grid 2 masih TAS di v6 → kode kosong, perlu divalidasi, teks tetap dibawa
    assert g(1, "Kode utama") == "" and g(1, "Status isian") == "perlu divalidasi"
    assert g(1, "Catatan").startswith("[v6] Kode F")
    # (a) grid 3: kode E
    assert g(2, "Kode utama") == pilihan("E") and g(2, "Status isian") == "perlu konfirmasi peneliti"
    # (e) grid 4: TES berbeda → arsip di Catatan saja
    assert g(3, "Kode utama") == "" and g(3, "Status isian") == "perlu divalidasi"
    assert g(3, "Catatan").startswith("Arsip v5 (TES terdekat berbeda") and g(3, "Penyebab (teks)") == ""
    # (e) grid 5: tidak ada di v5
    assert g(4, "Kode utama") == "" and g(4, "Catatan") == "" and g(4, "Status isian") == "perlu divalidasi"
    # (d) grid 1 Rendah tidak berubah → salin kode Baseline, otomatis; teks Rendah dibawa (TES sama, ΔT 0,5)
    assert g(5, "Kode utama") == pilihan("A") and g(5, "Status isian") == "otomatis"
    assert g(5, "Penyebab (teks)") == "Berada di lembah perbukitan" and g(5, "Catatan") == "catatan rendah"
    # (c) grid 1 Sedang diperparah → kode Baseline + G; kalimat umum v5 hanya arsip di Catatan
    assert g(6, "Kode utama") == pilihan("A") and g(6, "Kode tambahan") == pilihan("G")
    assert g(6, "Status isian") == "otomatis" and g(6, "Penyebab (teks)") == ""
    assert g(6, "Catatan").startswith("Arsip v5 (kalimat umum v5")
    # (b) dipicu → G otomatis
    assert g(7, "Kode utama") == pilihan("G") and g(7, "Kode tambahan") == "" and g(7, "Status isian") == "otomatis"
    # (d) tanpa kode Baseline (grid 2 berkode F dikosongkan) → perlu divalidasi
    assert g(8, "Kode utama") == "" and g(8, "Status isian") == "perlu divalidasi"
    # (e) lainnya → kosong
    assert g(9, "Kode utama") == "" and g(9, "Status isian") == "perlu divalidasi"
    # (c) grid 1 Tinggi diperparah
    assert g(10, "Kode tambahan") == pilihan("G") and g(10, "Status isian") == "otomatis"


def test_hotspot_dbscan_350m():
    df = pd.DataFrame({
        "id_grid": [1, 2, 3, 4, 4, 5], "level": ["Baseline", "Baseline", "Baseline", "Baseline", "Sedang", "Sedang"],
        "_x": [0.0, 300.0, 5000.0, 640.0, 640.0, 9000.0], "_y": [0.0] * 6,
        "Status isian": ["perlu divalidasi", "perlu konfirmasi peneliti", "perlu divalidasi", "otomatis",
                         "perlu divalidasi", "otomatis"],
        "Lat centroid": [-7.0] * 6, "Lon centroid": [110.0] * 6, "TES terdekat": ["a", "b", "c", "d", "d", "e"],
        "DI_t": [3.0, 9.0, 4.0, 2.5, 7.0, 5.0],
    })
    d, hs = add_hotspots(df)
    # grid 1, 2, 4 berantai ≤ 350 m → satu hotspot; grid 3 sendiri; grid 5 hanya "otomatis" → tanpa hotspot
    assert list(hs["Hotspot"]) == ["H01", "H02"] and list(hs["Jumlah grid"]) == [3, 1]
    assert hs.at[0, "id_grid"] == "1, 2, 4" and hs.at[0, "Level"] == "Baseline, Sedang" and hs.at[0, "DI maksimum"] == 9.0
    assert hs.at[0, "Google Maps satelit"] == "https://www.google.com/maps/@-7.000000,110.000000,18z/data=!3m1!1e3"
    assert list(d["Hotspot"].fillna("")) == ["H01", "H01", "H02", "H01", "H01", ""]

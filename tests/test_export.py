"""Logika ekspor Bab IV (Putaran 3): format angka, K utama bersama, penurunan ke tipologi terburuk."""
import json

import pandas as pd

import scripts.export_bab4 as E
from backend.config import k_utama_default


def test_format_angka_indonesia():
    assert E.id_num(12345.678, 2) == "12.345,68"
    assert E.id_num(7, 0) == "7"
    assert E.id_num(None) == "–"


def test_k_utama_satu_konfigurasi_untuk_export_dan_dashboard():
    k = json.loads(E.PENGATURAN.read_text(encoding="utf-8"))["k_utama"]
    assert E.k_utama_default() == k_utama_default() == k


def test_turun_ke_tipologi_terburuk():
    k = 3        # state 2 = terburuk, 3 = Tergenang
    grid = pd.DataFrame({"state_sedang_k3": [0, 1, 2, 3, 0, 1], "state_tinggi_k3": [2, 2, 2, 3, 3, 1]})
    assert E.worst_drop(grid, k) == 2


def test_finalisasi_metrik_ternormalisasi_hanya_yang_lulus_b3():
    S = {"status": {"DESC-N": {"lulus": True}, "PESC-N": {"lulus": False}}}
    assert E.lulus_b3(S) == ["DESC-N"] and E.lulus_b3(None) == []


def test_finalisasi_tabel_algoritma_memuat_guo_dan_metrik_baru():
    kon = [{"seed": 42 + i, "konvergen": i < 9} for i in range(10)]
    rows = [{"algoritma": "SDWFCM termodifikasi", "status": "ok", "silhouette": 0.2, "desc_n": 0.04,
             "klaster_terbesar_persen": 30.0, "ari_vs_sdwfcm_termodifikasi": 1.0},
            {"algoritma": "SDWFCM-Guo (λ = 0,5)", "status": "ok", "silhouette": 0.18, "konvergensi": kon,
             "klaster_terbesar_persen": 28.0, "ari_vs_sdwfcm_termodifikasi": 0.76},
            {"algoritma": "SKATER", "status": "gagal"}]
    t = E.tables_algo_finalisasi({"d_perbandingan_algoritma": {"4": rows}}, 4, "T")
    assert t.code == "T06" and list(t.df["Algoritma"]) == ["SDWFCM termodifikasi", "SDWFCM-Guo (λ = 0,5)", "SKATER"]
    for col in ("DESC-N", "PESC-N", "Kontiguitas", "Homogenitas", "I-Index", "Dunn", "ARI vs SDWFCM termodifikasi"):
        assert col in t.df.columns
    assert "konvergen 9/10" in t.note

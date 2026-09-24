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

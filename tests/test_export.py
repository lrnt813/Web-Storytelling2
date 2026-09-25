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


def test_id_num_membiarkan_teks():
    assert E.id_num("K = 4", 3) == "K = 4"


def _R_ketahanan():
    tr = lambda a, b, fr, to, c, sr, tg: {"from_level": a, "to_level": b, "dominant_transition": {"from": fr, "to": to, "count": c},
                                          "stability_rate": sr, "masuk_tergenang": tg}
    pairs = [("baseline", "rendah"), ("rendah", "sedang"), ("sedang", "tinggi"), ("baseline", "tinggi")]
    return {"model": {"4": {"transitions": [tr(a, b, 0, 4, 5, 90.0, 7) for a, b in pairs]},
                      "2": {"transitions": [tr(a, b, 0, 2, 9, 95.0, 7) for a, b in pairs]}}}


def test_ketahanan_k4_vs_k2():
    grid = pd.DataFrame({**{f"tas_status_{l}": [1, 1, 0, 3] for l in E.LEVEL_ORDER},
                         **{f"state_{l}_k4": [3, 1, 0, 4] for l in E.LEVEL_ORDER},
                         **{f"state_{l}_k2": [1, 1, 0, 2] for l in E.LEVEL_ORDER}})
    rows = E.ketahanan_rows(_R_ketahanan(), grid)
    tr = [r for r in rows if r["Bagian"] == "Transisi"]
    lv = [r for r in rows if r["Bagian"] != "Transisi"]
    assert len(tr) == 4 and tr[0]["K = 4: transisi dominan"] == "Tipologi 1 → Tergenang (di luar klasterisasi) (5)"
    assert lv[0]["K = 4: % grid di tipologi terburuk"] == 25.0 and lv[0]["K = 2: % grid di tipologi terburuk"] == 50.0
    assert lv[0]["K = 4: TAS di tipologi terburuk"] == 1 and lv[0]["K = 4: TAS di tipologi lain"] == 1
    assert lv[0]["K = 2: TAS di tipologi terburuk"] == 2 and lv[0]["K = 2: TAS di tipologi lain"] == 0
    teks = "\n".join(E.ringkasan_ketahanan(_R_ketahanan(), grid))
    assert "identik" in teks and "lebih rendah atau sama" in teks


def test_kriteria_k_final_menunjuk_argmax():
    from scripts.keputusan_k_v6 import kriteria_k_final
    c = lambda k, a, s, t, i, d: {"k": k, "ari_subsampel_mean": a, "silhouette": s, "ketegasan_partisi": t,
                                  "iidx": i, "dunn": d}
    R = {"k_selection": {"candidates": [c(2, .96, .24, .34, 1.2, .006), c(4, .95, .20, .46, 15.2, .0105),
                                        c(5, .94, .17, .41, 11.8, .0107)]}}
    F = {"b4_desc_n_v6": {"2": {"desc_n": .02, "pesc_n": .11}, "4": {"desc_n": .014, "pesc_n": .06},
                          "5": {"desc_n": .012, "pesc_n": .058}}}
    got = {r["Kriteria"]: r["K yang ditunjuk"] for r in kriteria_k_final(R, F)}
    assert got == {"Stabilitas subsampel (ARI)": 2, "Silhouette": 2, "Ketegasan partisi": 4, "I-Index": 4, "Dunn": 5,
                   "DESC-N": 2, "PESC-N": 2}


def test_t11g_dari_lembar_validasi(tmp_path):
    f = tmp_path / "lembar.xlsx"
    d = pd.DataFrame({"id_grid": [1, 2, 3, 4], "level": ["Baseline", "Baseline", "Sedang", "Sedang"],
                      "Atribusi banjir": [None, None, "dipicu banjir", "tidak berubah"],
                      "Kode utama": ["A Sungai/waduk", "E", "G Penutupan ruas akibat banjir", "B"]})
    with pd.ExcelWriter(f) as xw:
        d.to_excel(xw, sheet_name="Validasi TAS", index=False)
    t = E.tables_validasi_tas(f)[0]
    r = t.df.set_index("Level")
    assert t.code == "T11g" and r.at["Baseline", "TAS"] == 2
    assert r.at["Baseline", "TAS struktural (A/B/C/D) (grid)"] == 1 and r.at["Baseline", "Artefak data/metode (E/F/H) (%)"] == 50
    assert r.at["Sedang", "TAS akibat banjir (G) (grid)"] == 1 and r.at["Sedang", "Valid Y"] == 2
    assert E.tables_validasi_tas(tmp_path / "tidak_ada.xlsx") == []


def test_label_tipologi_deskriptif_dan_tergenang_terpisah():
    from backend.config import TERGENANG_LABEL, deskripsi_tipologi, label_tipologi
    for k in (2, 3, 4):
        d = deskripsi_tipologi(k)
        assert len(d) == k and all(v.strip() for v in d.values())
        assert label_tipologi(0, k).startswith("Tipologi 1: ") and label_tipologi(k, k) == TERGENANG_LABEL
    assert E.state_name(4, 4) == TERGENANG_LABEL and E.state_name(2, 4) == "Tipologi 3"
    assert E.tip(3, 4) == "Tipologi 4: " + deskripsi_tipologi(4)["3"]
    assert label_tipologi(0, 7) == "Tipologi 1"                    # tanpa deskripsi → hanya peringkat


def test_dashboard_memakai_label_deskriptif_tanpa_mengubah_hasil():
    from backend.config import deskripsi_tipologi
    from backend.main import _apply_display_labels
    R = {"model": {"4": {"cluster_names": {"0": "Tipologi 1 (terbaik)"},
                         "cluster_profile": [{"klaster": c, "deskripsi": "x"} for c in range(4)]}}}
    _apply_display_labels(R)
    assert R["model"]["4"]["cluster_names"] == deskripsi_tipologi(4)
    assert R["model"]["4"]["cluster_profile"][3]["deskripsi"].startswith("Tipologi 4: ")

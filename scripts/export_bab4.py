"""Ekspor seluruh tabel Bab IV dari hasil TERKUNCI (data/locked/) ke output_bab4/.

    python -m scripts.export_bab4

Keluaran:
  output_bab4/T*.csv                    satu CSV per tabel (angka mentah, titik desimal)
  output_bab4/Tabel_Bab4.docx           semua tabel, format angka Indonesia
                                        (koma desimal, titik ribuan; waktu 2 desimal, metrik 3 desimal)
  output_bab4/ringkasan_angka_bab4.md   angka kunci untuk narasi
  output_bab4/perbandingan_v1_vs_v2.md  angka kunci v1 (data/locked/arsip_v1/) vs v2 beserta
                                        perubahan metode penyebab perbedaannya

Skrip ini HANYA membaca data/locked/ (termasuk data/locked/arsip_v1/ untuk laporan perbandingan).
Folder output_bab4/arsip_v1/ tidak disentuh.
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCKED = PROJECT_ROOT / "data" / "locked"
ARSIP_V1 = LOCKED / "arsip_v1" / "thesis_results.json"
OUT = PROJECT_ROOT / "output_bab4"

KAT = ["pendidikan", "kesehatan", "pemerintahan", "ibadah", "gor"]
KAT_LABEL = {"pendidikan": "Pendidikan", "kesehatan": "Kesehatan", "pemerintahan": "Pemerintahan",
             "ibadah": "Tempat Ibadah", "gor": "GOR/Gedung Serbaguna"}
LEVEL_ORDER = ["baseline", "rendah", "sedang", "tinggi"]
LEVEL_LABEL = {"baseline": "Baseline", "rendah": "Rendah", "sedang": "Sedang", "tinggi": "Tinggi"}
VAR_LABEL = {**{f"waktu_tes_{k}": f"Waktu TES {v} (menit)" for k, v in KAT_LABEL.items()},
             "waktu_tes_min": "Waktu TES minimum (menit)"}


# ── format angka Indonesia ──────────────────────────────────────────────────
def id_num(v, dec=2):
    if v is None or (isinstance(v, float) and v != v):
        return "–"
    if isinstance(v, bool):
        return "Ya" if v else "Tidak"
    if isinstance(v, (int,)) and dec == 0:
        return f"{v:,}".replace(",", ".")
    s = f"{float(v):,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


class Table:
    """Tabel dengan data mentah (untuk CSV) dan format kolom (untuk DOCX)."""

    def __init__(self, code, title, df, fmt=None, note=""):
        self.code, self.title, self.df, self.fmt, self.note = code, title, df, fmt or {}, note

    def formatted(self):
        out = self.df.copy().astype(object)
        for col in out.columns:
            dec = self.fmt.get(col)
            if dec is not None:
                out[col] = [id_num(v, dec) for v in self.df[col]]
            else:
                out[col] = ["–" if (v is None or (isinstance(v, float) and v != v)) else str(v)
                            for v in self.df[col]]
        return out


def load_locked():
    lock = json.loads((LOCKED / "LOCK.json").read_text(encoding="utf-8"))
    res_path = LOCKED / "thesis_results.json"
    sha = hashlib.sha256(res_path.read_bytes()).hexdigest()
    if lock.get("files", {}).get("thesis_results.json") != sha:
        raise SystemExit("thesis_results.json di data/locked/ tidak cocok dengan checksum LOCK.json.")
    return json.loads(res_path.read_text(encoding="utf-8")), lock


def state_name(s, k):
    return "Tergenang" if s == k else f"K{s}"


# ── penyusun tabel ──────────────────────────────────────────────────────────
def build_tables(R):
    T = []
    lv = R["levels"]
    ds = R["data_summary"]
    k = R["k"]
    pool = R["data_gabungan"]

    rows = [("Grid analisis 100 × 100 m", ds["n_grid"]), ("Segmen jaringan jalan", ds["n_road_segments"])]
    rows += [(f"TES {KAT_LABEL[c]}", ds["tes_counts"][c]) for c in KAT]
    rows += [("TES total", sum(ds["tes_counts"].values())),
             ("Baris data gabungan (grid × level non-Tergenang)", pool["n_baris"])]
    T.append(Table("T01", "Ringkasan data spasial", pd.DataFrame(rows, columns=["Komponen", "Jumlah"]),
                   {"Jumlah": 0}, f"Sistem koordinat {ds['crs']}; kecepatan berjalan "
                   f"{id_num(R['meta']['walking_speed_m_per_min'], 0)} m/menit; waktu penalti "
                   f"T_pen = 3 × T_max Baseline = {id_num(R['t_pen'], 2)} menit."))

    rows = []
    for key in LEVEL_ORDER:
        d = lv[key]["diagnostik"]
        rows.append({"Level": LEVEL_LABEL[key], "Kelas bahaya ditutup": ", ".join(map(str, lv[key]["kelas_ditutup"])) or "tidak ada",
                     **{f"TES {KAT_LABEL[c]}": d["tes_valid_per_kategori"][c] for c in KAT},
                     "TES valid total": d["tes_valid_total"], "Ruas jalan ditutup": d["ruas_jalan_ditutup"],
                     "Baris data gabungan": pool["n_baris_per_level"][key]})
    df = pd.DataFrame(rows)
    T.append(Table("T02", "Definisi level, TES valid, dan ruas jalan ditutup", df,
                   {c: 0 for c in df.columns if c not in ("Level", "Kelas bahaya ditutup")},
                   "Level didefinisikan oleh kelas bahaya banjir InaRisk yang ditutup."))

    rows = []
    for key in LEVEL_ORDER:
        s, d = lv[key], lv[key]["diagnostik"]
        rows.append({"Level": LEVEL_LABEL[key], "Grid Tergenang": s["n_grid_tergenang"],
                     "% grid": s["persen_grid_tergenang"], "Grid non-Tergenang": s["n_grid_non_tergenang"],
                     "Tergenang & terisolasi": d["grid_terisolasi_tergenang"],
                     "Rerata waktu minimum grid Tergenang (menit, informasi)": s["mean_waktu_min_tergenang"]})
    df = pd.DataFrame(rows)
    T.append(Table("T03", "Grid Tergenang per level", df,
                   {"Grid Tergenang": 0, "% grid": 2, "Grid non-Tergenang": 0, "Tergenang & terisolasi": 0,
                    "Rerata waktu minimum grid Tergenang (menit, informasi)": 2},
                   "Grid Tergenang dikeluarkan dari klasterisasi dan TAS; waktu tempuhnya hanya informasi."))

    rows = [{"Variabel": VAR_LABEL[s["variabel"]], "n": s["jumlah"], "Rata-rata": s["mean"],
             "Simpangan baku": s["std"], "Min": s["min"], "Q1": s["q25"], "Median": s["median"],
             "Q3": s["q75"], "Maks": s["max"]} for s in R["baseline_time_stats"]]
    df = pd.DataFrame(rows)
    T.append(Table("T04", "Statistik deskriptif waktu tempuh ke TES pada Baseline (menit)", df,
                   {"n": 0} | {c: 2 for c in df.columns if c not in ("Variabel", "n")},
                   "Waktu = (ruas snapping centroid → jalan + jarak jaringan + ruas snapping jalan → TES) / 80 m/menit."))

    ks = R["k_selection"]
    rows = [{"K": c["k"], "ARI subsampel (rerata)": c["ari_subsampel_mean"], "ARI subsampel (sd)": c["ari_subsampel_sd"],
             "ARI inisialisasi (rerata)": c["ari_inisialisasi_mean"], "ARI inisialisasi (sd)": c["ari_inisialisasi_sd"],
             "I-Index": c["iidx"], "Dunn (rerata)": c["dunn"], "Dunn (sd)": c["dunn_sd"],
             "Ketegasan partisi": c["ketegasan_partisi"], "DESC": c["desc"], "PESC": c["pesc"],
             "Silhouette": c["silhouette"], "Size entropy": c["size_entropy"],
             "Klaster terbesar (%)": c["klaster_terbesar_persen"],
             "Komposit +DESC": c["komposit_dengan_desc"], "Komposit −DESC": c["komposit_tanpa_desc"],
             "Terpilih": "✓" if c["k"] == ks["k_terpilih"] else ""} for c in ks["candidates"]]
    df = pd.DataFrame(rows)
    fmt = {c: 3 for c in df.columns if c not in ("K", "Terpilih", "PESC", "Klaster terbesar (%)")}
    T.append(Table("T05", "Pemilihan K berbasis stabilitas (data gabungan)", df,
                   fmt | {"K": 0, "PESC": 6, "Klaster terbesar (%)": 2, "Dunn (rerata)": 4, "Dunn (sd)": 4},
                   f"Aturan (ditetapkan sebelum melihat hasil): K dengan rerata ARI subsampel tertinggi; bila beberapa K "
                   f"berselisih ≤ {id_num(ks['toleransi'], 2)} dari nilai tertinggi, dipilih K terkecil. "
                   f"{ks['B']} subsampel {id_num(ks['fraksi_subsampel'] * 100, 0)} % id_grid, {ks['n_init_subsampel']} "
                   f"inisialisasi per subsampel. K terpilih = {ks['k_terpilih']} (kandidat dalam toleransi: "
                   f"{', '.join(map(str, ks['k_dalam_toleransi']))}); runner-up K = {ks['k_runner_up']}. Metrik "
                   f"pendukung hanya dilaporkan; skor komposit lama memilih K = {ks['k_komposit_dengan_desc']} "
                   f"(+DESC) dan K = {ks['k_komposit_tanpa_desc']} (−DESC). DESC/PESC: blok rook; Dunn: 5 sampel 2.000 "
                   f"grid (seed 42–46); Silhouette: sampel 10.000 (seed 42)."))

    if R.get("algorithm_comparison"):
        rows = []
        for a in R["algorithm_comparison"]:
            rows.append({"Algoritma": a["algoritma"],
                         "Status": {"ok": "layak", "degeneratif": "degeneratif — tidak layak dibandingkan",
                                    "gagal": "gagal — tidak layak dibandingkan"}[a["status"]],
                         "Inisialisasi": a["n_init"], "Jumlah klaster": a.get("n_cluster"),
                         "Silhouette": a.get("silhouette"), "Calinski-Harabasz": a.get("calinski_harabasz"),
                         "Davies-Bouldin": a.get("davies_bouldin"), "Moran's I": a.get("moran_i"),
                         "p (Moran)": a.get("moran_p"), "Proporsi tetangga sama": a.get("proporsi_tetangga_sama"),
                         "Size entropy": a.get("size_entropy"), "Klaster terbesar (%)": a.get("klaster_terbesar_persen"),
                         "Waktu per inisialisasi (detik)": a["time_per_init_sec"], "Galat": a.get("galat", "")})
        df = pd.DataFrame(rows)
        T.append(Table("T06", f"Perbandingan algoritma pada Baseline (K = {k})", df,
                       {"Inisialisasi": 0, "Jumlah klaster": 0, "Silhouette": 3, "Calinski-Harabasz": 3,
                        "Davies-Bouldin": 3, "Moran's I": 3, "p (Moran)": 3, "Proporsi tetangga sama": 3,
                        "Size entropy": 3, "Klaster terbesar (%)": 2, "Waktu per inisialisasi (detik)": 2},
                       "FCM (α = 0), SFCM, dan SDWFCM: praproses data gabungan, K, 10 inisialisasi (J terkecil), dan "
                       "aturan penomoran yang sama. Moran's I label: 999 permutasi, kontiguitas rook. Degeneratif = "
                       "klaster terbesar > 90 % grid."))

    rows = []
    for p in R["cluster_profile"]:
        iso = sum(p[f"is_isolated_{c}"] or 0 for c in KAT) / len(KAT)
        rows.append({"Klaster": p["klaster"], "Jumlah baris": p["jumlah_baris"], "% baris": p["persen_baris"],
                     "Kepadatan jalan": p["Road_Density_mean"], "Kelas bahaya (deskriptif)": p["banjir"],
                     **{f"Waktu {KAT_LABEL[c]}": p[f"waktu_tes_{c}"] for c in KAT},
                     "Waktu minimum": p["waktu_tes_min"], "Opsi rute": p["jumlah_opsi_rute"],
                     "Terisolasi (proporsi)": p["is_isolated"],
                     "Proporsi kategori terisolasi": iso, "Interpretasi": p.get("deskripsi", "")})
    df = pd.DataFrame(rows)
    fmt = {"Klaster": 0, "Jumlah baris": 0, "% baris": 2, "Kepadatan jalan": 3, "Kelas bahaya (deskriptif)": 3,
           "Opsi rute": 2, "Terisolasi (proporsi)": 3, "Proporsi kategori terisolasi": 3}
    fmt |= {c: 2 for c in df.columns if c.startswith("Waktu")}
    T.append(Table("T07", "Profil tipologi SDWFCM (data gabungan keempat level)", df, fmt,
                   "Rata-rata nilai asli per klaster atas semua pasangan grid–level non-Tergenang (waktu dalam menit). "
                   "Klaster 0 = rata-rata waktu tempuh minimum terkecil (akses terbaik). Kelas bahaya bukan fitur."))

    rows = []
    for key in LEVEL_ORDER:
        row = {"Level": LEVEL_LABEL[key]}
        for d in lv[key]["distribusi_tipologi"]:
            nm = "Tergenang" if d["nama"] == "Tergenang" else f"K{d['state']}"
            row[f"{nm} (grid)"] = d["jumlah_grid"]
            row[f"{nm} (%)"] = d["persen_semua_grid"]
        rows.append(row)
    df = pd.DataFrame(rows)
    T.append(Table("T08", "Distribusi tipologi dan Tergenang per level", df,
                   {c: (0 if c.endswith("(grid)") else 2) for c in df.columns if c != "Level"},
                   "Persentase terhadap seluruh grid."))

    for i, t in enumerate(R["transitions"]):
        S = k + 1
        M = pd.DataFrame(t["matrix"], columns=[f"ke {state_name(j, k)}" for j in range(S)])
        M.insert(0, "Dari", [state_name(j, k) for j in range(S)])
        T.append(Table(f"T09{chr(97 + i)}", f"Matriks transisi {LEVEL_LABEL[t['from_level']]} → "
                       f"{LEVEL_LABEL[t['to_level']]} (jumlah grid)", M, {c: 0 for c in M.columns if c != "Dari"}))
    rows = []
    for t in R["transitions"]:
        d = t["dominant_transition"]
        rows.append({"Transisi": f"{LEVEL_LABEL[t['from_level']]} → {LEVEL_LABEL[t['to_level']]}",
                     "Masuk Tergenang (grid)": t["masuk_tergenang"],
                     "Masuk Tergenang (% semua grid)": t["persen_masuk_tergenang_semua_grid"],
                     "Masuk Tergenang (% non-Tergenang awal)": t["persen_masuk_tergenang_dari_non_tergenang_awal"],
                     "Grid non-Tergenang di kedua level": t["n_non_tergenang_kedua_level"],
                     "Stability rate (%)": t["stability_rate"], "ARI": t["ari"],
                     "Transisi dominan": f"{state_name(d['from'], k)} → {state_name(d['to'], k)}" if d else "–",
                     "Jumlah (dominan)": d["count"] if d else None,
                     "Dominan menuju": d["menuju"] if d else "–",
                     "Active edges": t["active_edges"], "Edge mungkin": (k + 1) * k,
                     "Active edges antar-tipologi": t["active_edges_antar_tipologi"], "CDVM": t["cdvm"]})
    df = pd.DataFrame(rows)
    T.append(Table("T10", "Ringkasan transisi antarlevel (state tipologi + Tergenang)", df,
                   {"Masuk Tergenang (grid)": 0, "Masuk Tergenang (% semua grid)": 2,
                    "Masuk Tergenang (% non-Tergenang awal)": 2, "Grid non-Tergenang di kedua level": 0,
                    "Stability rate (%)": 2, "ARI": 3, "Jumlah (dominan)": 0, "Active edges": 0, "Edge mungkin": 0,
                    "Active edges antar-tipologi": 0, "CDVM": 3},
                   "Stability rate dan ARI hanya pada grid non-Tergenang di kedua level. Transisi dominan = sel "
                   "terbesar di luar diagonal matriks (K+1) × (K+1). CDVM = ½ Σ_s |p_s(tujuan) − p_s(asal)| atas "
                   "K tipologi + Tergenang."))

    rows = []
    for key in LEVEL_ORDER:
        s = lv[key]["tas"]
        sen = s["sensitivitas_di_absolut"]
        rows.append({"Level": LEVEL_LABEL[key], "TAS": s["jumlah_tas"], "Non-TAS": s["jumlah_non_tas"],
                     "Terputus": s["jumlah_terputus"], "Tergenang": s["jumlah_tergenang"],
                     "% TAS (semua grid)": s["persen_tas"], "% TAS (non-Tergenang)": s["persen_tas_non_tergenang"],
                     "% TAS (terjangkau)": s["persen_tas_terjangkau"],
                     "Rerata DI TAS": s["mean_di_tas"], "Rerata DI Non-TAS": s["mean_di_non_tas"],
                     "Selisih DI": s["delta_di"], "P25 T_ideal (menit)": s["p25_t_ideal"], "P75 DI": s["p75_di"],
                     "TAS (DI ≥ 2)": sen["jumlah_tas"], "% TAS (DI ≥ 2)": sen["persen_tas"],
                     "% TAS yang juga DI ≥ 2": sen["persen_tas_juga_lolos_absolut"]})
    df = pd.DataFrame(rows)
    fmt = {c: 0 for c in ("TAS", "Non-TAS", "Terputus", "Tergenang", "TAS (DI ≥ 2)")}
    fmt |= {c: 2 for c in df.columns if c.startswith("%")}
    fmt |= {"Rerata DI TAS": 3, "Rerata DI Non-TAS": 3, "Selisih DI": 3, "P25 T_ideal (menit)": 2, "P75 DI": 3}
    T.append(Table("T11", "Titik Aman Semu per level (4 kategori)", df, fmt,
                   "TAS jika T_ideal ≤ P25(T_ideal) dan DI_t ≥ P75(DI_t), persentil dari grid non-Tergenang yang "
                   "terjangkau. T_ideal dan T_aktual sama-sama centroid → titik TES dengan batas minimum 50 m. "
                   "Kolom DI ≥ 2: uji sensitivitas ambang absolut."))

    rows = []
    for key in LEVEL_ORDER:
        d = lv[key]["diagnostik"]
        kb = d["kelas_bahaya"]
        rows.append({"Level": LEVEL_LABEL[key], "Grid Tergenang": d["grid_tergenang"],
                     "Terisolasi (non-Tergenang)": d["grid_terisolasi_non_tergenang"],
                     "Terisolasi (Tergenang)": d["grid_terisolasi_tergenang"],
                     "Ruas ditutup": d["ruas_jalan_ditutup"],
                     "Kelas ditutup (aturan)": ", ".join(map(str, kb["kelas_ditutup_aturan"])) or "–",
                     "Kelas grid Tergenang (data)": ", ".join(map(str, kb["grid_tergenang_kelas_data"])) or "–",
                     "Kelas ruas ditutup (data)": ", ".join(map(str, kb["ruas_ditutup_kelas_data"])) or "–",
                     "Aturan = data": kb["konsisten"],
                     "TAS: T_aktual < T_ideal": lv[key]["tas"].get("jumlah_t_aktual_lt_t_ideal")})
    df = pd.DataFrame(rows)
    T.append(Table("T12", "Diagnostik per level", df,
                   {"Grid Tergenang": 0, "Terisolasi (non-Tergenang)": 0, "Terisolasi (Tergenang)": 0,
                    "Ruas ditutup": 0, "Aturan = data": 0, "TAS: T_aktual < T_ideal": 0},
                   "Terisolasi = jumlah_opsi_rute = 0. Kolom terakhir harus 0 (T_aktual ≥ T_ideal)."))

    rows = [{"Level": LEVEL_LABEL[key], "Rata-rata waktu minimum": lv[key]["mean_waktu_min"],
             "Median waktu minimum": lv[key]["median_waktu_min"],
             **{f"Rata-rata {KAT_LABEL[c]}": lv[key]["mean_waktu"][c] for c in KAT}} for key in LEVEL_ORDER]
    df = pd.DataFrame(rows)
    T.append(Table("T13", "Rata-rata waktu tempuh ke TES per level, grid non-Tergenang (menit)", df,
                   {c: 2 for c in df.columns if c != "Level"}))

    pp = R["preprocessing"]
    mf = R["model_final"]
    rows = [{"Tahap": "Data fit", "Nilai": f"data gabungan, {id_num(pp['n_baris_fit'], 0)} baris"},
            {"Tahap": "Fitur masukan", "Nilai": ", ".join(pp["features_in"])},
            {"Tahap": "Fitur terpilih", "Nilai": ", ".join(pp["features_kept"])},
            {"Tahap": "Fitur dibuang", "Nilai": ", ".join(pp["features_dropped"]) or "–"},
            {"Tahap": "Capping 3 × IQR", "Nilai": "; ".join(f"{c}: [{id_num(a, 3)}; {id_num(b, 3)}]"
                                                           for c, (a, b) in pp["caps"].items())},
            {"Tahap": "Komponen PCA", "Nilai": id_num(pp["n_components"], 0)},
            {"Tahap": "Varians kumulatif PCA", "Nilai": id_num(pp["explained_variance"] * 100, 2) + " %"},
            {"Tahap": "σ kernel Gaussian per level (m)",
             "Nilai": "; ".join(f"{LEVEL_LABEL[k2]} {id_num(v, 2)}" for k2, v in pool["sigma_per_level"].items())},
            {"Tahap": "Model final", "Nilai": f"seed {mf['seed_terbaik']}, J = {id_num(mf['objective'], 3)}"}]
    T.append(Table("T14", "Pra-pemrosesan (di-fit sekali pada data gabungan) dan model final", pd.DataFrame(rows)))

    v = mf["validity"]
    rows = [{"Metrik": "I-Index", "Nilai": v["iidx"]}, {"Metrik": "Ketegasan partisi", "Nilai": v["ketegasan_partisi"]},
            {"Metrik": "Dunn (rerata 5 sampel)", "Nilai": v["dunn"]["mean"]},
            {"Metrik": "Dunn (sd 5 sampel)", "Nilai": v["dunn"]["sd"]},
            {"Metrik": "DESC (blok rook)", "Nilai": v["desc"]}, {"Metrik": "PESC (km)", "Nilai": v["pesc"]},
            {"Metrik": "Silhouette (sampel 10.000)", "Nilai": v["silhouette_sampel"]},
            {"Metrik": "Size entropy", "Nilai": v["size_entropy"]},
            {"Metrik": "Proporsi tetangga rook berlabel sama", "Nilai": v["proporsi_tetangga_sama"]}]
    T.append(Table("T15", f"Validitas model final (data gabungan, K = {k})", pd.DataFrame(rows), {"Nilai": 4}))
    return T


# ── keluaran ────────────────────────────────────────────────────────────────
def write_csv(tables):
    for old in OUT.glob("T*.csv"):
        old.unlink()
    for t in tables:
        t.df.to_csv(OUT / f"{t.code}_{_slug(t.title)}.csv", index=False, encoding="utf-8-sig")


def _slug(s):
    import re
    return re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_")[:70]


def write_docx(tables, R, lock):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Cm, Pt

    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.5))
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(9)

    doc.add_heading("Tabel Bab IV — hasil terkunci", level=1)
    doc.add_paragraph(f"Sumber: data/locked/ (commit analisis {lock['git']['commit_analisis'][:10]}, "
                      f"dikunci {lock['locked_at']}). Format angka Indonesia; waktu 2 desimal, metrik 3 desimal.")
    for t in tables:
        doc.add_heading(f"{t.code}. {t.title}", level=2)
        f = t.formatted()
        table = doc.add_table(rows=1, cols=len(f.columns))
        table.style = "Table Grid"
        for j, col in enumerate(f.columns):
            cell = table.rows[0].cells[j]
            cell.text = str(col)
            for r in cell.paragraphs[0].runs:
                r.font.bold = True
                r.font.size = Pt(8)
        for _, row in f.iterrows():
            cells = table.add_row().cells
            for j, val in enumerate(row):
                cells[j].text = str(val)
                for r in cells[j].paragraphs[0].runs:
                    r.font.size = Pt(8)
        if t.note:
            p = doc.add_paragraph(t.note)
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.italic = True
    doc.save(OUT / "Tabel_Bab4.docx")


def write_summary(R, lock):
    lv, ks, k = R["levels"], R["k_selection"], R["k"]
    L = ["# Ringkasan angka kunci Bab IV", "",
         f"Sumber: `data/locked/` — commit analisis `{lock['git']['commit_analisis']}`, "
         f"dikunci {lock['locked_at']}. Semua angka dalam format Indonesia.", "",
         "## Data", "",
         f"- Jumlah grid analisis: **{id_num(R['data_summary']['n_grid'], 0)}**",
         f"- Jumlah segmen jalan: **{id_num(R['data_summary']['n_road_segments'], 0)}**",
         f"- Jumlah TES: **{id_num(sum(R['data_summary']['tes_counts'].values()), 0)}** ("
         + ", ".join(f"{KAT_LABEL[c]} {id_num(R['data_summary']['tes_counts'][c], 0)}" for c in KAT) + ")",
         f"- Waktu penalti T_pen (3 × T_max Baseline): **{id_num(R['t_pen'], 2)} menit**",
         f"- Data gabungan: **{id_num(R['data_gabungan']['n_baris'], 0)} baris** ("
         + ", ".join(f"{LEVEL_LABEL[x]} {id_num(R['data_gabungan']['n_baris_per_level'][x], 0)}" for x in LEVEL_ORDER) + ")", ""]
    base_min = next(s for s in R["baseline_time_stats"] if s["variabel"] == "waktu_tes_min")
    L += ["## Waktu tempuh Baseline (termasuk ruas snapping)", "",
          f"- Rata-rata waktu tempuh minimum: **{id_num(base_min['mean'], 2)} menit**",
          f"- Median waktu tempuh minimum: **{id_num(base_min['median'], 2)} menit**",
          f"- Kuartil ketiga waktu tempuh minimum: **{id_num(base_min['q75'], 2)} menit**", ""]
    pp = R["preprocessing"]
    L += ["## Pra-pemrosesan (data gabungan)", "",
          f"- Fitur terpilih: **{len(pp['features_kept'])} dari {len(pp['features_in'])}** "
          f"({', '.join(pp['features_kept'])})",
          f"- Komponen PCA: **{pp['n_components']}** (varians kumulatif **{id_num(pp['explained_variance'] * 100, 2)} %**)", ""]
    sel = next(c for c in ks["candidates"] if c["k"] == ks["k_terpilih"])
    L += ["## Pemilihan K (stabilitas)", "",
          f"- K terpilih: **{ks['k_terpilih']}** (rerata ARI subsampel {id_num(sel['ari_subsampel_mean'], 3)} ± "
          f"{id_num(sel['ari_subsampel_sd'], 3)}; ARI inisialisasi {id_num(sel['ari_inisialisasi_mean'], 3)})",
          f"- Nilai tertinggi {id_num(ks['ari_subsampel_tertinggi'], 3)} pada K = {ks['k_ari_tertinggi']}; kandidat dalam "
          f"toleransi {id_num(ks['toleransi'], 2)}: {', '.join(map(str, ks['k_dalam_toleransi']))}",
          f"- Runner-up: K = {ks['k_runner_up']} (ARI {id_num(ks['ari_runner_up'], 3)}); selisih "
          f"{id_num(ks['selisih_ari_terpilih_vs_runner_up'], 3)}",
          f"- Sensitivitas skor komposit lama: +DESC → K = {ks['k_komposit_dengan_desc']}, −DESC → K = {ks['k_komposit_tanpa_desc']}", ""]
    if R.get("algorithm_comparison"):
        L += ["## Perbandingan algoritma (Baseline)", ""]
        for a in R["algorithm_comparison"]:
            if a["status"] == "gagal":
                L.append(f"- {a['algoritma']}: **gagal** ({a['galat']}) — tidak layak dibandingkan")
                continue
            tag = "" if a["status"] == "ok" else " — **degeneratif, tidak layak dibandingkan**"
            L.append(f"- {a['algoritma']}{tag}: Silhouette {id_num(a.get('silhouette'), 3)}, CH {id_num(a.get('calinski_harabasz'), 3)}, "
                     f"DB {id_num(a.get('davies_bouldin'), 3)}, Moran's I {id_num(a.get('moran_i'), 3)}, "
                     f"tetangga sama {id_num(a.get('proporsi_tetangga_sama'), 3)}, klaster terbesar "
                     f"{id_num(a.get('klaster_terbesar_persen'), 2)} %")
        L.append("")
    L += ["## Profil tipologi (data gabungan)", ""]
    for p in R["cluster_profile"]:
        L.append(f"- K{p['klaster']}: {id_num(p['jumlah_baris'], 0)} baris ({id_num(p['persen_baris'], 2)} %), waktu minimum "
                 f"{id_num(p['waktu_tes_min'], 2)} menit, opsi rute {id_num(p['jumlah_opsi_rute'], 2)} — {p.get('deskripsi', '')}")
    L += ["", "## Per level", ""]
    for key in LEVEL_ORDER:
        s, d, t = lv[key], lv[key]["diagnostik"], lv[key]["tas"]
        dist = ", ".join(f"{'Tergenang' if x['nama'] == 'Tergenang' else 'K' + str(x['state'])} = "
                         f"{id_num(x['jumlah_grid'], 0)} ({id_num(x['persen_semua_grid'], 2)} %)" for x in s["distribusi_tipologi"])
        L += [f"### {s['label_lengkap']}", "",
              f"- Grid Tergenang: **{id_num(s['n_grid_tergenang'], 0)}** ({id_num(s['persen_grid_tergenang'], 2)} %)",
              f"- Ruas jalan ditutup: **{id_num(d['ruas_jalan_ditutup'], 0)}**; TES valid: **{id_num(d['tes_valid_total'], 0)}**",
              f"- Rata-rata waktu tempuh minimum (non-Tergenang): **{id_num(s['mean_waktu_min'], 2)} menit**",
              f"- TAS **{id_num(t['jumlah_tas'], 0)}** ({id_num(t['persen_tas_non_tergenang'], 2)} % grid non-Tergenang); "
              f"Non-TAS {id_num(t['jumlah_non_tas'], 0)}; Terputus {id_num(t['jumlah_terputus'], 0)}; Tergenang {id_num(t['jumlah_tergenang'], 0)}",
              f"- Rerata DI TAS / Non-TAS: **{id_num(t['mean_di_tas'], 3)} / {id_num(t['mean_di_non_tas'], 3)}**; TAS yang juga DI ≥ 2: "
              f"{id_num(t['sensitivitas_di_absolut']['persen_tas_juga_lolos_absolut'], 2)} %",
              f"- Distribusi: {dist}", ""]
    L += ["## Transisi", ""]
    for t in R["transitions"]:
        d = t["dominant_transition"]
        L.append(f"- {LEVEL_LABEL[t['from_level']]} → {LEVEL_LABEL[t['to_level']]}: masuk Tergenang "
                 f"**{id_num(t['masuk_tergenang'], 0)}** ({id_num(t['persen_masuk_tergenang_semua_grid'], 2)} %); stability rate "
                 f"**{id_num(t['stability_rate'], 2)} %**, ARI **{id_num(t['ari'], 3)}** (grid non-Tergenang di kedua level); "
                 f"dominan {state_name(d['from'], k)} → {state_name(d['to'], k)} ({id_num(d['count'], 0)} grid, {d['menuju']}); "
                 f"active edges {t['active_edges']}; CDVM {id_num(t['cdvm'], 3)}")
    (OUT / "ringkasan_angka_bab4.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_v1_v2(R):
    """Angka kunci v1 vs v2 dan perubahan metode penyebab perbedaan."""
    if not ARSIP_V1.exists():
        return
    V1 = json.loads(ARSIP_V1.read_text(encoding="utf-8"))
    l1, l2 = V1["levels"], R["levels"]
    rows = []

    def add(nama, a, b, dec, sebab):
        rows.append(f"| {nama} | {id_num(a, dec)} | {id_num(b, dec)} | {sebab} |")

    base1 = next(s for s in V1["baseline_time_stats"] if s["variabel"] == "waktu_tes_min")
    base2 = next(s for s in R["baseline_time_stats"] if s["variabel"] == "waktu_tes_min")
    add("T_pen (menit)", V1["t_pen"], R["t_pen"], 2, "Langkah 3: waktu tempuh memuat ruas snapping (T_max Baseline berubah)")
    add("Rata-rata waktu minimum Baseline (menit)", base1["mean"], base2["mean"], 2, "Langkah 3: ruas snapping")
    add("Median waktu minimum Baseline (menit)", base1["median"], base2["median"], 2, "Langkah 3: ruas snapping")
    add("Jumlah fitur klasterisasi", len(V1["preprocessing"]["features_in"]), len(R["preprocessing"]["features_in"]), 0,
        "Langkah 5: kelas bahaya banjir bukan fitur")
    add("Komponen PCA", V1["preprocessing"]["n_components"], R["preprocessing"]["n_components"], 0,
        "Langkah 5 + 6: 9 fitur, praproses di-fit pada data gabungan (bukan Baseline)")
    add("Varians kumulatif PCA (%)", V1["preprocessing"]["explained_variance"] * 100,
        R["preprocessing"]["explained_variance"] * 100, 2, "Langkah 5 + 6")
    add("K terpilih", V1["k"], R["k"], 0, "Langkah 7: aturan stabilitas subsampel menggantikan skor komposit; Langkah 6: data gabungan")
    for key in LEVEL_ORDER:
        d1, d2 = l1[key]["diagnostik"], l2[key]["diagnostik"]
        add(f"Grid terdampak/Tergenang — {LEVEL_LABEL[key]}", d1["grid_terdampak"], d2["grid_tergenang"], 0,
            "Tidak ada perubahan himpunan (Langkah 2 membuktikan aturan kelas = aturan intensitas lama)")
        add(f"Ruas ditutup — {LEVEL_LABEL[key]}", d1["ruas_jalan_ditutup"], d2["ruas_jalan_ditutup"], 0, "Sama (Langkah 2)")
        add(f"TES valid — {LEVEL_LABEL[key]}", d1["tes_valid_total"], d2["tes_valid_total"], 0, "Sama (aturan TES tidak diubah)")
    for key in LEVEL_ORDER:
        add(f"Rata-rata waktu minimum — {LEVEL_LABEL[key]} (menit)", l1[key]["mean_waktu_min"], l2[key]["mean_waktu_min"], 2,
            "Langkah 3 (ruas snapping) + Langkah 4 (v2: rata-rata grid non-Tergenang; v1: semua grid)")
    for key in LEVEL_ORDER:
        t1, t2 = l1[key]["tas"], l2[key]["tas"]
        add(f"TAS — {LEVEL_LABEL[key]}", t1["jumlah_tas"], t2["jumlah_tas"], 0,
            "Langkah 3 (T_aktual memuat ruas snapping, batas 50 m di kedua jarak) + Langkah 4 (grid Tergenang dikeluarkan dari persentil)")
        add(f"Terputus — {LEVEL_LABEL[key]}", t1["jumlah_terputus"], t2["jumlah_terputus"], 0,
            "Langkah 4: v1 Terputus mencakup grid terdampak; v2 grid tersebut berstatus Tergenang")
        add(f"Rerata DI TAS — {LEVEL_LABEL[key]}", t1["mean_di_tas"], t2["mean_di_tas"], 3, "Langkah 3 + 4")
        add(f"Rerata DI Non-TAS — {LEVEL_LABEL[key]}", t1["mean_di_non_tas"], t2["mean_di_non_tas"], 3, "Langkah 3 + 4")
    tr1 = {(t["from_level"], t["to_level"]): t for t in V1["transitions"]}
    for t in R["transitions"]:
        pair = (t["from_level"], t["to_level"])
        nm = f"{LEVEL_LABEL[pair[0]]} → {LEVEL_LABEL[pair[1]]}"
        a = tr1.get(pair)
        add(f"Stability rate {nm} (%)", a["stability_rate"] if a else None, t["stability_rate"], 2,
            "Langkah 6 (satu model gabungan, tanpa Hungarian) + Langkah 10 (dihitung pada grid non-Tergenang di kedua level)"
            + ("" if a else "; pasangan baru di v2"))
        add(f"ARI {nm}", a["ari"] if a else None, t["ari"], 3, "Langkah 6 + 10" + ("" if a else "; pasangan baru di v2"))
    a1 = {a["algoritma"]: a for a in V1.get("algorithm_comparison", [])}
    for a in R.get("algorithm_comparison", []):
        b = a1.get(a["algoritma"])
        sebab = ("Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; " +
                 ("algoritma baru di v2" if b is None else "fitur 9 (Langkah 5)"))
        add(f"Silhouette {a['algoritma']}", b["silhouette"] if b else None, a.get("silhouette"), 3, sebab)
        add(f"Moran's I {a['algoritma']}", b["moran_i"] if b else None, a.get("moran_i"), 3,
            sebab + "; Moran 999 permutasi (v1: 99)")
        if a["algoritma"] == "SKATER":
            rows.append(f"| Status SKATER | fallback MST manual | {a['status']} | Langkah 8: spopt `floor`, fallback dihapus |")
        if a["algoritma"] == "REDCAP":
            rows.append(f"| Status REDCAP | dilaporkan tanpa penanda | {a['status']} | Langkah 8: penanda degeneratif (> 90 %) |")

    L = ["# Perbandingan angka kunci v1 vs v2", "",
         "v1 = `data/locked/arsip_v1/` (tag `hasil-skripsi-v1`); v2 = `data/locked/` (tag `hasil-skripsi-v2`). "
         "**Angka v2 yang berlaku.** Kolom terakhir menyebut perubahan metode (putaran 2) yang menyebabkan perbedaan.", "",
         "| Angka | v1 | v2 | Perubahan metode penyebab |", "|---|---:|---:|---|", *rows, "",
         "Catatan: nomor klaster v1 dan v2 tidak dapat dipasangkan satu-satu (v1: model per level + Hungarian; "
         "v2: satu model gabungan), sehingga profil per klaster tidak dibandingkan per nomor."]
    (OUT / "perbandingan_v1_vs_v2.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    R, lock = load_locked()
    OUT.mkdir(exist_ok=True)
    for old in ("perbandingan_draft_vs_final.md",):      # laporan v1 (tersimpan di output_bab4/arsip_v1/)
        (OUT / old).unlink(missing_ok=True)
    tables = build_tables(R)
    write_csv(tables)
    write_docx(tables, R, lock)
    write_summary(R, lock)
    write_v1_v2(R)
    print(f"{len(tables)} tabel diekspor ke {OUT}")


if __name__ == "__main__":
    sys.exit(main())

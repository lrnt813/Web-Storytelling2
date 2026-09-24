"""Ekspor seluruh tabel Bab IV dari hasil TERKUNCI (data/locked/) ke output_bab4/.

    python -m scripts.export_bab4

Keluaran:
  output_bab4/T*.csv                       satu CSV per tabel (angka mentah, titik desimal)
  output_bab4/Tabel_Bab4.docx              semua tabel, format angka Indonesia
                                           (koma desimal, titik ribuan; waktu 2 desimal, metrik 3 desimal)
  output_bab4/ringkasan_angka_bab4.md      angka kunci untuk narasi
  output_bab4/perbandingan_draft_vs_final.md  angka draft lama vs hasil final (bantuan revisi teks)

Skrip ini HANYA membaca data/locked/ (dan docs/angka_draft_lama.json untuk laporan perbandingan).
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCKED = PROJECT_ROOT / "data" / "locked"
OUT = PROJECT_ROOT / "output_bab4"
DRAFT = PROJECT_ROOT / "docs" / "angka_draft_lama.json"

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


# ── penyusun tabel ──────────────────────────────────────────────────────────
def build_tables(R):
    T = []
    lv = R["levels"]
    ds = R["data_summary"]

    rows = [("Grid analisis 100 × 100 m", ds["n_grid"]), ("Segmen jaringan jalan", ds["n_road_segments"])]
    rows += [(f"TES {KAT_LABEL[k]}", ds["tes_counts"][k]) for k in KAT]
    rows += [("TES total", sum(ds["tes_counts"].values()))]
    T.append(Table("T01", "Ringkasan data spasial", pd.DataFrame(rows, columns=["Komponen", "Jumlah"]),
                   {"Jumlah": 0}, f"Sistem koordinat {ds['crs']}; kecepatan berjalan "
                   f"{id_num(R['meta']['walking_speed_m_per_min'], 0)} m/menit; waktu penalti "
                   f"T_pen = {id_num(R['t_pen'], 2)} menit."))

    rows = []
    for key in LEVEL_ORDER:
        d = lv[key]["diagnostik"]
        rows.append({"Level": LEVEL_LABEL[key], "Intensitas": lv[key]["intensity"],
                     **{f"TES {KAT_LABEL[k]}": d["tes_valid_per_kategori"][k] for k in KAT},
                     "TES valid total": d["tes_valid_total"], "Grid terdampak": d["grid_terdampak"],
                     "Ruas jalan ditutup": d["ruas_jalan_ditutup"]})
    df = pd.DataFrame(rows)
    T.append(Table("T02", "TES valid, grid terdampak, dan ruas jalan ditutup per level", df,
                   {c: 0 for c in df.columns if c not in ("Level", "Intensitas")} | {"Intensitas": 2}))

    rows = [{"Variabel": VAR_LABEL[s["variabel"]], "n": s["jumlah"], "Rata-rata": s["mean"],
             "Simpangan baku": s["std"], "Min": s["min"], "Q1": s["q25"], "Median": s["median"],
             "Q3": s["q75"], "Maks": s["max"]} for s in R["baseline_time_stats"]]
    df = pd.DataFrame(rows)
    T.append(Table("T03", "Statistik deskriptif waktu tempuh ke TES pada Baseline (menit)", df,
                   {"n": 0} | {c: 2 for c in df.columns if c not in ("Variabel", "n")}))

    ks = R["k_selection"]
    rows = [{"K": c["k"], "I-Index": c["iidx"], "Dunn": c["dunn"], "DESC": c["desc"],
             "Ketegasan partisi": c["ketegasan_partisi"], "PESC": c["pesc"],
             "Size entropy": c["size_entropy"], "Parsimoni": c["parsimoni"], "Skor komposit": c["composite"],
             "Terpilih": "✓" if c["k"] == ks["k_terpilih"] else ""} for c in ks["candidates"]]
    df = pd.DataFrame(rows)
    T.append(Table("T04", "Evaluasi kandidat K pada Baseline", df,
                   {"K": 0, "I-Index": 3, "Dunn": 3, "DESC": 3, "Ketegasan partisi": 3, "PESC": 6,
                    "Size entropy": 3, "Parsimoni": 3, "Skor komposit": 3},
                   f"Skor komposit = rata-rata percentile rank I-Index, Dunn, DESC, ketegasan partisi dan "
                   f"parsimoni linear. K terpilih = {ks['k_terpilih']} (skor {id_num(ks['skor_terpilih'], 3)}); "
                   f"runner-up K = {ks['k_runner_up']} (skor {id_num(ks['skor_runner_up'], 3)}); "
                   f"selisih {id_num(ks['selisih_skor'], 3)}."))

    if R.get("algorithm_comparison"):
        rows = [{"Algoritma": a["algoritma"], "Jumlah klaster": a["n_cluster"], "Silhouette": a["silhouette"],
                 "Calinski-Harabasz": a["calinski_harabasz"], "Davies-Bouldin": a["davies_bouldin"],
                 "Moran's I": a["moran_i"], "p (Moran)": a["moran_p"], "Size entropy": a["size_entropy"],
                 "Proporsi tetangga sama": a["proporsi_tetangga_sama"], "WCSS": a["wcss"],
                 "Waktu (detik)": a["time_sec"]} for a in R["algorithm_comparison"]]
        df = pd.DataFrame(rows)
        T.append(Table("T05", f"Perbandingan algoritma pada Baseline (K = {R['k']})", df,
                       {"Jumlah klaster": 0, "Silhouette": 3, "Calinski-Harabasz": 3, "Davies-Bouldin": 3,
                        "Moran's I": 3, "p (Moran)": 3, "Size entropy": 3, "Proporsi tetangga sama": 3,
                        "WCSS": 3, "Waktu (detik)": 2},
                       "Semua algoritma dinomori dengan aturan yang sama (urut rata-rata waktu_tes_min) sebelum "
                       "Moran's I dihitung. Waktu SDWFCM = rata-rata per inisialisasi."))

    for i, key in enumerate(LEVEL_ORDER):
        rows = []
        for p in lv[key]["cluster_profile"]:
            iso = sum(p[f"is_isolated_{k}"] or 0 for k in KAT) / len(KAT)
            rows.append({"Klaster": p["klaster"], "Jumlah grid": p["jumlah_grid"], "% grid": p["persen_grid"],
                         "Kepadatan jalan": p["Road_Density_mean"], "Indeks bahaya": p["banjir"],
                         **{f"Waktu {KAT_LABEL[k]}": p[f"waktu_tes_{k}"] for k in KAT},
                         "Waktu minimum": p["waktu_tes_min"], "Opsi rute": p["jumlah_opsi_rute"],
                         "Proporsi kategori terisolasi": iso, "Interpretasi": p.get("deskripsi", "")})
        df = pd.DataFrame(rows)
        fmt = {"Klaster": 0, "Jumlah grid": 0, "% grid": 2, "Kepadatan jalan": 3, "Indeks bahaya": 3,
               "Opsi rute": 2, "Proporsi kategori terisolasi": 3}
        fmt |= {c: 2 for c in df.columns if c.startswith("Waktu")}
        al = lv[key].get("penyelarasan_label")
        note = "Nomor klaster: urut rata-rata waktu tempuh minimum (Baseline)." if al is None else (
            "Nomor klaster diselaraskan ke pusat Baseline (Hungarian). Tipologi baru/tidak berpadanan: "
            + (", ".join(str(p["klaster"]) for p in al["pasangan"] if p["tipologi_baru"]) or "tidak ada") + ".")
        T.append(Table(f"T06{chr(97 + i)}", f"Profil klaster SDWFCM level {LEVEL_LABEL[key]}", df, fmt,
                       "Waktu dalam menit (rata-rata per klaster). " + note))

    rows = []
    for key in LEVEL_ORDER[1:]:
        for p in lv[key]["penyelarasan_label"]["pasangan"]:
            rows.append({"Level": LEVEL_LABEL[key], "Klaster": p["klaster"],
                         "Jarak ke pusat Baseline": p["jarak_ke_pusat_baseline"],
                         "Batas (2 × median jarak antarpusat Baseline)": lv[key]["penyelarasan_label"]["batas_tipologi_baru"],
                         "Tipologi baru": p["tipologi_baru"]})
    df = pd.DataFrame(rows)
    T.append(Table("T07", "Penyelarasan label klaster ke pusat Baseline", df,
                   {"Klaster": 0, "Jarak ke pusat Baseline": 3, "Batas (2 × median jarak antarpusat Baseline)": 3,
                    "Tipologi baru": 0}))

    k = R["k"]
    for i, t in enumerate(R["transitions"]):
        M = pd.DataFrame(t["matrix"], columns=[f"ke K{j}" for j in range(k)])
        M.insert(0, "Dari", [f"K{j}" for j in range(k)])
        T.append(Table(f"T08{chr(97 + i)}", f"Matriks transisi {LEVEL_LABEL[t['from_level']]} → "
                       f"{LEVEL_LABEL[t['to_level']]} (jumlah grid)", M, {c: 0 for c in M.columns if c != "Dari"}))
    rows = [{"Transisi": f"{LEVEL_LABEL[t['from_level']]} → {LEVEL_LABEL[t['to_level']]}",
             "Stability rate (%)": t["stability_rate"], "ARI": t["ari"], "Grid berpindah": t["n_moved"],
             "Transisi dominan": f"K{t['dominant_transition']['from']} → K{t['dominant_transition']['to']}",
             "Jumlah (dominan)": t["dominant_transition"]["count"],
             "Active edges": t["active_edges"], "Edge mungkin": k * (k - 1),
             "CDVM vs Baseline": R["cdvm_vs_baseline"][t["to_level"]]} for t in R["transitions"]]
    df = pd.DataFrame(rows)
    T.append(Table("T09", "Ringkasan transisi klaster antarlevel", df,
                   {"Stability rate (%)": 2, "ARI": 3, "Grid berpindah": 0, "Jumlah (dominan)": 0,
                    "Active edges": 0, "Edge mungkin": 0, "CDVM vs Baseline": 3},
                   "Dihitung setelah penyelarasan label. CDVM = ½ Σ |p_k(level) − p_k(Baseline)|."))

    rows = []
    for key in LEVEL_ORDER:
        s = lv[key]["tas"]
        sen = s["sensitivitas_di_absolut"]
        rows.append({"Level": LEVEL_LABEL[key], "TAS": s["jumlah_tas"], "Non-TAS": s["jumlah_non_tas"],
                     "Terputus": s["jumlah_terputus"], "% TAS (semua grid)": s["persen_tas"],
                     "% TAS (grid terjangkau)": s["persen_tas_terjangkau"],
                     "Rerata DI TAS": s["mean_di_tas"], "Rerata DI Non-TAS": s["mean_di_non_tas"],
                     "Selisih DI": s["delta_di"], "P25 T_ideal (menit)": s["p25_t_ideal"], "P75 DI": s["p75_di"],
                     f"TAS (DI ≥ {id_num(sen['ambang_di'], 0)})": sen["jumlah_tas"],
                     f"% TAS (DI ≥ {id_num(sen['ambang_di'], 0)})": sen["persen_tas"]})
    df = pd.DataFrame(rows)
    fmt = {c: 0 for c in ("TAS", "Non-TAS", "Terputus")} | {c: 2 for c in df.columns if c.startswith("%")}
    fmt |= {"Rerata DI TAS": 3, "Rerata DI Non-TAS": 3, "Selisih DI": 3, "P25 T_ideal (menit)": 2, "P75 DI": 3}
    fmt |= {c: 0 for c in df.columns if c.startswith("TAS (DI")}
    T.append(Table("T10", "Titik Aman Semu per level", df, fmt,
                   "TAS jika T_ideal ≤ P25(T_ideal) dan DI_t ≥ P75(DI_t), dihitung pada grid terjangkau; "
                   "grid dengan T_aktual = T_pen = Terputus. Jarak Euclidean minimum 50 m. Kolom DI ≥ 2: uji "
                   "sensitivitas dengan ambang absolut."))

    rows = []
    for key in LEVEL_ORDER:
        d = lv[key]["diagnostik"]
        kb = d["kelas_bahaya"]
        rows.append({"Level": LEVEL_LABEL[key], "Grid terisolasi": d["grid_terisolasi"],
                     "Terisolasi & terdampak": d["grid_terisolasi_terdampak"],
                     "Terisolasi & tidak terdampak": d["grid_terisolasi_tidak_terdampak"],
                     "Grid terdampak": d["grid_terdampak"], "Ruas ditutup": d["ruas_jalan_ditutup"],
                     "Kelas bahaya grid terdampak": ", ".join(map(str, kb["grid_terdampak_kelas_data"])) or "–",
                     "Kelas bahaya ruas ditutup": ", ".join(map(str, kb["ruas_ditutup_kelas_data"])) or "–",
                     "Aturan = data": kb["konsisten"]})
    df = pd.DataFrame(rows)
    T.append(Table("T11", "Diagnostik per level", df,
                   {"Grid terisolasi": 0, "Terisolasi & terdampak": 0, "Terisolasi & tidak terdampak": 0,
                    "Grid terdampak": 0, "Ruas ditutup": 0, "Aturan = data": 0},
                   "Grid terisolasi = jumlah_opsi_rute = 0. Kelas bahaya diverifikasi dari aturan kode dan data."))

    rows = []
    for key in LEVEL_ORDER:
        for p in lv[key]["diagnostik"]["proporsi_terdampak_per_klaster"]:
            rows.append({"Level": LEVEL_LABEL[key], "Klaster": p["klaster"], "Jumlah grid": p["jumlah_grid"],
                         "Grid terdampak": p["jumlah_terdampak"], "Proporsi terdampak": p["proporsi_terdampak"]})
    df = pd.DataFrame(rows)
    T.append(Table("T12", "Proporsi grid terdampak di setiap klaster", df,
                   {"Klaster": 0, "Jumlah grid": 0, "Grid terdampak": 0, "Proporsi terdampak": 3}))

    rows = [{"Level": LEVEL_LABEL[key], "Rata-rata waktu minimum": lv[key]["mean_waktu_min"],
             "Median waktu minimum": lv[key]["median_waktu_min"],
             **{f"Rata-rata {KAT_LABEL[k]}": lv[key]["mean_waktu"][k] for k in KAT}} for key in LEVEL_ORDER]
    df = pd.DataFrame(rows)
    T.append(Table("T13", "Rata-rata waktu tempuh ke TES per level (menit)", df,
                   {c: 2 for c in df.columns if c != "Level"}))

    pp = R["preprocessing"]
    rows = [{"Tahap": "Fitur masukan", "Nilai": ", ".join(pp["features_in"])},
            {"Tahap": "Fitur terpilih (seleksi di Baseline)", "Nilai": ", ".join(pp["features_kept"])},
            {"Tahap": "Fitur dibuang", "Nilai": ", ".join(pp["features_dropped"]) or "–"},
            {"Tahap": "Capping 3 × IQR", "Nilai": "; ".join(f"{c}: [{id_num(a, 3)}; {id_num(b, 3)}]"
                                                           for c, (a, b) in pp["caps"].items())},
            {"Tahap": "Komponen PCA", "Nilai": id_num(pp["n_components"], 0)},
            {"Tahap": "Varians kumulatif PCA", "Nilai": id_num(pp["explained_variance"] * 100, 2) + " %"}]
    T.append(Table("T14", "Pra-pemrosesan (di-fit pada Baseline)", pd.DataFrame(rows)))
    return T


# ── keluaran ────────────────────────────────────────────────────────────────
def write_csv(tables):
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
            for j, v in enumerate(row):
                cells[j].text = str(v)
                for r in cells[j].paragraphs[0].runs:
                    r.font.size = Pt(8)
        if t.note:
            p = doc.add_paragraph(t.note)
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.italic = True
    doc.save(OUT / "Tabel_Bab4.docx")


def write_summary(R, lock):
    lv, ks = R["levels"], R["k_selection"]
    L = ["# Ringkasan angka kunci Bab IV", "",
         f"Sumber: `data/locked/` — commit analisis `{lock['git']['commit_analisis']}`, "
         f"dikunci {lock['locked_at']}. Semua angka dalam format Indonesia.", "",
         "## Data", "",
         f"- Jumlah grid analisis: **{id_num(R['data_summary']['n_grid'], 0)}**",
         f"- Jumlah segmen jalan: **{id_num(R['data_summary']['n_road_segments'], 0)}**",
         f"- Jumlah TES: **{id_num(sum(R['data_summary']['tes_counts'].values()), 0)}** ("
         + ", ".join(f"{KAT_LABEL[k]} {id_num(R['data_summary']['tes_counts'][k], 0)}" for k in KAT) + ")",
         f"- Waktu penalti T_pen (3 × T_max Baseline): **{id_num(R['t_pen'], 2)} menit**", ""]
    base_min = next(s for s in R["baseline_time_stats"] if s["variabel"] == "waktu_tes_min")
    L += ["## Waktu tempuh Baseline", "",
          f"- Rata-rata waktu tempuh minimum: **{id_num(base_min['mean'], 2)} menit**",
          f"- Median waktu tempuh minimum: **{id_num(base_min['median'], 2)} menit**",
          f"- Kuartil ketiga waktu tempuh minimum: **{id_num(base_min['q75'], 2)} menit**", ""]
    pp = R["preprocessing"]
    L += ["## Pra-pemrosesan", "",
          f"- Fitur terpilih: **{len(pp['features_kept'])} dari {len(pp['features_in'])}** "
          f"({', '.join(pp['features_kept'])})",
          f"- Komponen PCA: **{pp['n_components']}** (varians kumulatif **{id_num(pp['explained_variance'] * 100, 2)} %**)", ""]
    L += ["## Pemilihan K", "",
          f"- K terpilih: **{ks['k_terpilih']}** (skor komposit {id_num(ks['skor_terpilih'], 3)})",
          f"- Runner-up: K = {ks['k_runner_up']} (skor {id_num(ks['skor_runner_up'], 3)}); "
          f"selisih skor **{id_num(ks['selisih_skor'], 3)}**", ""]
    if R.get("algorithm_comparison"):
        L += ["## Perbandingan algoritma (Baseline)", ""]
        for a in R["algorithm_comparison"]:
            L.append(f"- {a['algoritma']}: Silhouette {id_num(a['silhouette'], 3)}, CH {id_num(a['calinski_harabasz'], 3)}, "
                     f"DB {id_num(a['davies_bouldin'], 3)}, Moran's I {id_num(a['moran_i'], 3)}, "
                     f"proporsi tetangga sama {id_num(a['proporsi_tetangga_sama'], 3)}, WCSS {id_num(a['wcss'], 3)}")
        L.append("")
    L += ["## Per level", ""]
    for key in LEVEL_ORDER:
        s, d, t = lv[key], lv[key]["diagnostik"], lv[key]["tas"]
        L += [f"### {LEVEL_LABEL[key]}", "",
              f"- Grid terdampak: **{id_num(d['grid_terdampak'], 0)}** ({id_num(s['persen_grid_terdampak'], 2)} %)",
              f"- Ruas jalan ditutup: **{id_num(d['ruas_jalan_ditutup'], 0)}**; TES valid: **{id_num(d['tes_valid_total'], 0)}**",
              f"- Rata-rata waktu tempuh minimum: **{id_num(s['mean_waktu_min'], 2)} menit**",
              f"- Grid terisolasi: **{id_num(d['grid_terisolasi'], 0)}** "
              f"(terdampak {id_num(d['grid_terisolasi_terdampak'], 0)}, tidak terdampak {id_num(d['grid_terisolasi_tidak_terdampak'], 0)})",
              f"- TAS: **{id_num(t['jumlah_tas'], 0)}** ({id_num(t['persen_tas'], 2)} % semua grid); Non-TAS "
              f"{id_num(t['jumlah_non_tas'], 0)}; Terputus {id_num(t['jumlah_terputus'], 0)}",
              f"- Rerata DI TAS / Non-TAS: **{id_num(t['mean_di_tas'], 3)} / {id_num(t['mean_di_non_tas'], 3)}**",
              f"- TAS dengan ambang absolut DI ≥ 2: {id_num(t['sensitivitas_di_absolut']['jumlah_tas'], 0)}",
              "- Ukuran klaster: " + ", ".join(f"K{p['klaster']} = {id_num(p['jumlah_grid'], 0)} "
                                               f"({id_num(p['persen_grid'], 2)} %)" for p in s["cluster_profile"]), ""]
    L += ["## Transisi", ""]
    for t in R["transitions"]:
        L.append(f"- {LEVEL_LABEL[t['from_level']]} → {LEVEL_LABEL[t['to_level']]}: stability rate "
                 f"**{id_num(t['stability_rate'], 2)} %**, ARI **{id_num(t['ari'], 3)}**, transisi dominan "
                 f"K{t['dominant_transition']['from']} → K{t['dominant_transition']['to']} "
                 f"({id_num(t['dominant_transition']['count'], 0)} grid), active edges {t['active_edges']}")
    (OUT / "ringkasan_angka_bab4.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_draft_comparison(R):
    if not DRAFT.exists():
        return
    D = json.loads(DRAFT.read_text(encoding="utf-8"))
    lv = R["levels"]
    L = ["# Perbandingan angka draft lama vs hasil final", "",
         "Bantuan revisi teks. Angka draft berasal dari `docs/angka_draft_lama.json`; angka final dari "
         "`data/locked/`. **Angka final yang berlaku.** Perbedaan mencerminkan koreksi metode "
         "(lihat docs/CATATAN_TEMUAN.md dan docs/METODOLOGI.md), bukan galat pembulatan.", ""]

    L += ["## Tabel 9 — statistik waktu tempuh Baseline (menit)", "",
          "| Variabel | Statistik | Draft | Final |", "|---|---|---:|---:|"]
    names = ["mean", "std", "min", "q25", "median", "q75", "max"]
    for s in R["baseline_time_stats"]:
        d = D["tabel_9_statistik_waktu_baseline"].get(s["variabel"])
        if d:
            for i, n in enumerate(names):
                L.append(f"| {s['variabel']} | {n} | {id_num(d[i], 2)} | {id_num(s[n], 2)} |")
    L.append("")

    dk = D["tabel_10_kandidat_k"]
    L += ["## Tabel 10 — kandidat K", "",
          f"K terpilih: draft **{dk['k_terpilih']}**, final **{R['k']}**.", "",
          "| K | I-Index draft | I-Index final | Ketegasan (draft 'CDVM') | Ketegasan final | Dunn draft | Dunn final | DESC draft | DESC final |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in R["k_selection"]["candidates"]:
        d = dk.get(str(c["k"]))
        if d:
            L.append(f"| {c['k']} | {id_num(d[0], 3)} | {id_num(c['iidx'], 3)} | {id_num(d[1], 3)} | "
                     f"{id_num(c['ketegasan_partisi'], 3)} | {id_num(d[2], 3)} | {id_num(c['dunn'], 3)} | "
                     f"{id_num(d[3], 3)} | {id_num(c['desc'], 3)} |")
    L.append("")

    if R.get("algorithm_comparison"):
        da = D["tabel_11_perbandingan_algoritma"]
        cols = [("silhouette", 0), ("calinski_harabasz", 1), ("davies_bouldin", 2), ("moran_i", 3),
                ("size_entropy", 4), ("wcss", 5)]
        L += ["## Tabel 11 — perbandingan algoritma", "",
              "| Algoritma | Metrik | Draft | Final |", "|---|---|---:|---:|"]
        for a in R["algorithm_comparison"]:
            d = da.get(a["algoritma"])
            if d:
                for name, i in cols:
                    L.append(f"| {a['algoritma']} | {name} | {id_num(d[i], 3)} | {id_num(a[name], 3)} |")
        L.append("")

    dp = D["tabel_12_15_profil_klaster"]
    L += ["## Tabel 12–15 — ukuran klaster", "",
          "Nomor klaster draft bersifat arbitrer sehingga tidak dipasangkan satu-satu; yang dibandingkan adalah "
          "sebaran ukuran klaster (diurutkan dari terbesar).", "",
          "| Level | Draft (terurut) | Final (terurut) |", "|---|---|---|"]
    for key in LEVEL_ORDER:
        dsz = sorted((row[-1] for row in dp[key]), reverse=True)
        fsz = sorted((p["jumlah_grid"] for p in lv[key]["cluster_profile"]), reverse=True)
        L.append(f"| {LEVEL_LABEL[key]} | {', '.join(id_num(v, 0) for v in dsz)} | "
                 f"{', '.join(id_num(v, 0) for v in fsz)} |")
    L.append("")

    dt = D["transisi"]
    L += ["## Transisi", "", "| Transisi | SR draft (%) | SR final (%) | ARI draft | ARI final |",
          "|---|---:|---:|---:|---:|"]
    for t in R["transitions"]:
        k = f"{t['from_level']}-{t['to_level']}"
        L.append(f"| {LEVEL_LABEL[t['from_level']]} → {LEVEL_LABEL[t['to_level']]} | "
                 f"{id_num(dt['stability_rate_persen'].get(k), 0)} | {id_num(t['stability_rate'], 2)} | "
                 f"{id_num(dt['ari'].get(k), 2)} | {id_num(t['ari'], 3)} |")
    L.append("")

    d16 = D["tabel_16_tas"]
    L += ["## Tabel 16 — Titik Aman Semu", "",
          "Definisi final berbeda: grid Terputus dikeluarkan, persentil dari grid terjangkau, jarak minimum 50 m.", "",
          "| Level | TAS draft | TAS final | % draft | % final | DI TAS draft | DI TAS final | DI Non-TAS draft | DI Non-TAS final | Terputus final |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key in LEVEL_ORDER:
        d, t = d16[key], lv[key]["tas"]
        L.append(f"| {LEVEL_LABEL[key]} | {id_num(d[0], 0)} | {id_num(t['jumlah_tas'], 0)} | {id_num(d[1], 2)} | "
                 f"{id_num(t['persen_tas'], 2)} | {id_num(d[2], 2)} | {id_num(t['mean_di_tas'], 3)} | "
                 f"{id_num(d[3], 2)} | {id_num(t['mean_di_non_tas'], 3)} | {id_num(t['jumlah_terputus'], 0)} |")
    L.append("")
    (OUT / "perbandingan_draft_vs_final.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    R, lock = load_locked()
    OUT.mkdir(exist_ok=True)
    tables = build_tables(R)
    write_csv(tables)
    write_docx(tables, R, lock)
    write_summary(R, lock)
    write_draft_comparison(R)
    print(f"{len(tables)} tabel diekspor ke {OUT}")


if __name__ == "__main__":
    sys.exit(main())

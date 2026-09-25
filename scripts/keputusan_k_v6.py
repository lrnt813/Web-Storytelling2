"""Dokumen keputusan K utama v6 (Finalisasi v6), dari hasil TERKUNCI hasil-skripsi-v6.

    python -m scripts.keputusan_k_v6

Menulis docs/KEPUTUSAN_K_v6.md: (a) tabel stabilitas K; (b) pemeriksaan adaptasi aturan one-standard-error;
(c) K terbaik menurut setiap kriteria, pusat klaster K = 3 dan K = 4, dan komponen I-Index; (d) profil
tipologi K = 2 dan K = 4 serta tabel silang; (e) transisi dominan K = 2 vs K = 4; (f) riwayat keputusan K;
(g) keputusan final (tabel kriteria → K yang ditunjuk → catatan keandalan; `kriteria_k_final` dipakai juga oleh
scripts/export_bab4.py).
Tidak menjalankan klasterisasi: pusat dan komponen I-Index dihitung dari skor PCA dan keanggotaan terkunci.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import TERGENANG_LABEL, label_tipologi

LOCKED = PROJECT_ROOT / "data" / "locked"
DOC = PROJECT_ROOT / "docs" / "KEPUTUSAN_K_v6.md"
LEVEL = {"baseline": "Baseline", "rendah": "Rendah", "sedang": "Sedang", "tinggi": "Tinggi"}


def kriteria_k_final(R, F=None, S=None):
    """Tabel keputusan final: kriteria → K yang ditunjuk (argmax pada hasil terkunci / metrik Finalisasi v6) →
    catatan keandalan. F = metrik_finalisasi_v6.json, S = validasi_sintetis.json (opsional)."""
    cands = R["k_selection"]["candidates"]
    best = lambda key: int(max(cands, key=lambda c: c[key])["k"])
    rows = [
        ("Stabilitas subsampel (ARI)", best("ari_subsampel_mean"),
         "Himpunan setara (selisih ≤ 0,01) = {2}; K = 4 berselisih 0,011 (juga di luar 1 sd dan 1 SE)."),
        ("Silhouette", best("silhouette"), "Tidak spasial; menilai pemisahan di ruang atribut."),
        ("Ketegasan partisi", best("ketegasan_partisi"), "Keanggotaan dihitung ulang di ruang atribut."),
        ("I-Index", best("iidx"),
         "Terdongkrak klaster baris penalti (DK 2,8 → 11,2 dari K = 3 ke K = 4); pada data buatan gagal menemukan K "
         "sebenarnya (tertinggi di K = 2, padahal K = 4)."),
        ("Dunn", best("dunn"),
         "Tidak membedakan K = 4 dan K = 5 (0,0105 vs 0,0107; selisih jauh di bawah sd antarsampel ± 0,004)."),
    ]
    if F:
        b4 = F["b4_desc_n_v6"]
        bn = lambda key: int(max(b4, key=lambda k: b4[k][key]))
        lul = (S or {}).get("status", {})
        rows += [
            ("DESC-N", bn("desc_n"),
             "Lulus validasi data buatan hanya lewat klausul \"tidak monoton\" (tertinggi di K = "
             f"{lul.get('DESC-N', {}).get('K_tertinggi', '–')}); memihak partisi kontigu."),
            ("PESC-N", bn("pesc_n"),
             "Satu-satunya metrik yang memenuhi validasi data buatan secara penuh (tertinggi di K sebenarnya = "
             f"{lul.get('PESC-N', {}).get('K_tertinggi', '–')}); memihak partisi kontigu."),
        ]
    return [{"Kriteria": a, "K yang ditunjuk": b, "Catatan keandalan": c} for a, b, c in rows]


def f(v, d=3):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    s = f"{v:,.{d}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def table(head, rows):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def one_se(cands, B):
    """Selisih rerata ARI subsampel tiap K terhadap K terbaik vs ambang 0,01, 1 sd K terbaik, dan 1 SE = sd/√B."""
    best = max(cands, key=lambda c: c["ari_subsampel_mean"])
    sd = best["ari_subsampel_sd"]
    se = sd / np.sqrt(B)
    rows = []
    for c in cands:
        d = best["ari_subsampel_mean"] - c["ari_subsampel_mean"]
        rows.append({"k": c["k"], "selisih": d, "tol": d <= 0.01 + 1e-12, "sd": d <= sd + 1e-12, "se": d <= se + 1e-12})
    return best, sd, se, rows


def iindex_parts(X, labels, centers):
    """Komponen I-Index (Maulik & Bandyopadhyay, 2002; p = 2): E1, EK, DK, dan nilai akhir."""
    ks = sorted(set(labels.tolist()))
    E1 = float(np.linalg.norm(X - X.mean(axis=0), axis=1).sum())
    EK = float(sum(np.linalg.norm(X[labels == c] - centers[c], axis=1).sum() for c in ks))
    from scipy.spatial.distance import cdist
    D = cdist(centers, centers)
    i, j = np.unravel_index(np.argmax(D), D.shape)
    K = len(ks)
    return {"E1": E1, "EK": EK, "E1/EK": E1 / EK, "DK": float(D.max()), "pasangan_DK": (int(i), int(j)),
            "I": float(((1.0 / K) * (E1 / EK) * D.max()) ** 2)}


def main():
    R = json.loads((LOCKED / "thesis_results.json").read_text(encoding="utf-8"))
    pool = pd.read_csv(LOCKED / "thesis_pooled_results.csv.gz")
    t_pen = float(R["t_pen"])
    ks = R["k_selection"]
    cands = ks["candidates"]
    m = float(R["meta"]["sdwfcm"]["m"])
    pcs = [c for c in pool.columns if c.startswith("pc")]
    X = pool[pcs].values
    L = ["# Keputusan K utama v6", "",
         "Sumber: hasil terkunci `hasil-skripsi-v6` (`data/locked/`). Dokumen ini dibuat oleh "
         "`python -m scripts.keputusan_k_v6` dan tidak menjalankan klasterisasi ulang. **Keputusan: K utama = 4** "
         "(peneliti bersama pembimbing) atas **dasar substantif**; METODOLOGI §9 (h). Keputusan ditetapkan **setelah** "
         "semua hasil terlihat; ringkasannya di bagian (g), riwayatnya di bagian (f).", ""]

    # (a)
    L += ["## (a) Tabel stabilitas K v6 (data gabungan)", "",
          f"{ks['B']} subsampel {f(ks['fraksi_subsampel'] * 100, 0)} % id_grid; ARI inisialisasi = rerata 45 pasangan "
          "run seed 42–51.", ""]
    L += table(["K", "ARI subsampel (rerata)", "ARI subsampel (sd)", "ARI inisialisasi", "Silhouette",
                "Ketegasan partisi", "Size entropy", "Klaster terbesar (%)"],
               [[c["k"], f(c["ari_subsampel_mean"], 4), f(c["ari_subsampel_sd"], 4), f(c["ari_inisialisasi_mean"], 4),
                 f(c["silhouette"]), f(c["ketegasan_partisi"]), f(c["size_entropy"]), f(c["klaster_terbesar_persen"], 1)]
                for c in cands]) + [""]

    # (b)
    best, sd, se, rows = one_se(cands, ks["B"])
    L += ["## (b) Pemeriksaan adaptasi aturan one-standard-error", "",
          "Aturan one-standard-error (Hastie, Tibshirani & Friedman, 2009, *The Elements of Statistical Learning*, "
          "ed. 2, hlm. 61 dan 244) memilih model paling sederhana yang berada dalam satu standard error dari model "
          "terbaik. Adaptasinya di sini: K terbaik = rerata ARI subsampel tertinggi "
          f"(K = {best['k']}, {f(best['ari_subsampel_mean'], 4)} ± {f(sd, 4)}); tiap K dibandingkan dengan tiga ambang: "
          f"toleransi 0,01 (aturan v2–v6), 1 sd K terbaik ({f(sd, 4)}), dan 1 SE = sd/√{ks['B']} ({f(se, 4)}).", ""]
    L += table(["K", "Selisih dari K terbaik", "≤ 0,01", "≤ 1 sd", "≤ 1 SE"],
               [[r["k"], f(r["selisih"], 4)] + ["Ya" if r[x] else "Tidak" for x in ("tol", "sd", "se")] for r in rows])
    L += ["", f"K = 4 berselisih {f(next(r['selisih'] for r in rows if r['k'] == 4), 4)} dan tidak berada dalam ambang "
          "mana pun. Catatan: subsampel 80 % saling tumpang tindih (setiap pasang subsampel berbagi sebagian besar grid), "
          "sehingga nilai ARI antar-subsampel tidak saling bebas dan SE = sd/√B cenderung terlalu kecil; ambang 1 SE "
          "karena itu lebih ketat dari yang semestinya. Dengan ketiga ambang, stabilitas tetap menunjuk K = 2 saja.", ""]

    # (c)
    crit = {"Stabilitas (ARI subsampel)": "ari_subsampel_mean", "Silhouette": "silhouette", "I-Index": "iidx",
            "Dunn": "dunn", "Ketegasan partisi": "ketegasan_partisi"}
    rows = []
    for name, key in crit.items():
        c1 = max(cands, key=lambda c: c[key])
        c4 = next(c for c in cands if c["k"] == 4)
        rows.append([name, c1["k"], f(c1[key], 4), f(c4[key], 4)])
    L += ["## (c) K terbaik menurut setiap kriteria", ""]
    L += table(["Kriteria", "K terbaik", "Nilai pada K terbaik", "Nilai pada K = 4"], rows)
    L += ["", "I-Index dan ketegasan partisi menunjuk K = 4; Dunn menunjuk K = 5 dengan selisih sangat kecil dari K = 4 "
          f"({f(next(c for c in cands if c['k'] == 5)['dunn'], 4)} vs {f(next(c for c in cands if c['k'] == 4)['dunn'], 4)}; "
          "Dunn dihitung pada sampel 2.000 baris). Stabilitas dan Silhouette menunjuk K = 2.", ""]
    L += ["### Pusat klaster K = 3 dan K = 4 dan komponen I-Index", "",
          "Pusat fuzzy (bobot u^m, m = " + f(m, 1) + ") di ruang PCA, dihitung dari keanggotaan terkunci (dibulatkan 6 "
          "desimal); kolom terakhir = rerata waktu minimum dan % baris bernilai penalti (T_pen) pada anggota klaster "
          "(label tegas).", ""]
    parts = {}
    for K in (2, 3, 4):
        U = pool[[f"u{c}_k{K}" for c in range(K)]].values
        lab = pool[f"klaster_k{K}"].values
        Um = U ** m
        C = (Um.T @ X) / Um.sum(axis=0)[:, None]
        parts[K] = iindex_parts(X, lab, C)
        if K in (3, 4):
            rows = []
            for c in range(K):
                sel = lab == c
                w = pool.loc[sel, "waktu_tes_min"].values
                rows.append([f"K{c} (Tipologi {c + 1})"] + [f(v) for v in C[c]]
                            + [f(w.mean(), 2), f((w >= t_pen - 1e-3).mean() * 100, 1)])
            L += [f"**K = {K}**", ""] + table(["Klaster"] + pcs + ["Rerata waktu min. (menit)", "% baris penalti"], rows) + [""]
    L += table(["K", "E1", "EK", "E1/EK", "DK (jarak pusat terjauh)", "Pasangan DK", "I-Index (dihitung ulang)",
                "I-Index (terkunci)"],
               [[K, f(p["E1"], 1), f(p["EK"], 1), f(p["E1/EK"]), f(p["DK"]), f"K{p['pasangan_DK'][0]}–K{p['pasangan_DK'][1]}",
                 f(p["I"]), f(next(c for c in cands if c["k"] == K)["iidx"])] for K, p in parts.items()])
    L += ["", "Lonjakan I-Index dari K = 3 ke K = 4 bertepatan dengan terbentuknya klaster baris bernilai penalti "
          "(Tipologi 4): DK naik tajam karena pusat klaster penalti jauh dari pusat lain, dan EK turun karena baris "
          "penalti yang beratribut hampir identik terkumpul pada satu pusat. Jadi I-Index pada K = 4 terutama "
          "mencerminkan pemisahan kelompok Terputus, bukan pemisahan yang merata di seluruh data.", ""]

    # (d)
    L += ["## (d) Profil tipologi K = 2 dan K = 4 (v6)", ""]
    rows = []
    for K in ("2", "4"):
        for p in R["model"][K]["cluster_profile"]:
            rows.append([f"K = {K}", label_tipologi(p["klaster"], int(K)), f(p["jumlah_baris"], 0), f(p["persen_baris"], 2),
                         f(p["waktu_tes_min_median"], 2), f(p["waktu_tes_min_p90"], 2),
                         f(p["waktu_tes_min_persen_penalti"], 2), f(p["proporsi_terputus"] * 100, 2)])
    L += table(["Model", "Tipologi", "Baris", "% baris", "Median waktu min. (menit)", "P90 waktu min. (menit)",
                "% baris penalti (waktu min.)", "% Terputus"], rows)
    ct = R["tabulasi_silang"]["k2_k4"]
    L += ["", f"**Tabel silang K = 2 × K = 4** (baris data gabungan; ARI antar-partisi {f(ct['ari'])}):", ""]
    L += table(["K = 2 \\ K = 4"] + [label_tipologi(j, 4) for j in range(len(ct["kolom"]))],
               [[label_tipologi(i, 2)] + [f(v, 0) for v in row] for i, row in enumerate(ct["matrix"])])
    p4 = R["model"]["4"]["cluster_profile"][-1]
    pisah = p4["proporsi_terputus"] > 0.5
    L += ["", f"**Titik berhenti A3:** K = 4 v6 {'MASIH' if pisah else 'TIDAK LAGI'} memisahkan tipologi Terputus. "
          f"{label_tipologi(p4['klaster'], 4)} berisi {f(p4['jumlah_baris'], 0)} baris ({f(p4['persen_baris'], 2)} %), dengan "
          f"{f(p4['proporsi_terputus'] * 100, 1)} % baris Terputus (waktu minimum = T_pen). Pada K = 2, baris Terputus "
          f"tersebar dalam Tipologi 2 ({f(R['model']['2']['cluster_profile'][1]['proporsi_terputus'] * 100, 1)} % dari "
          "klaster itu).", ""]

    # (e)
    L += ["## (e) Temuan utama K = 2 dan K = 4: transisi antarlevel", ""]
    rows = []
    tr = {K: {(t["from_level"], t["to_level"]): t for t in R["model"][K]["transitions"]} for K in ("2", "4")}
    sn = lambda s, K: TERGENANG_LABEL if s == int(K) else f"Tipologi {s + 1}"
    for pair in tr["4"]:
        cells = [f"{LEVEL[pair[0]]} → {LEVEL[pair[1]]}"]
        for K in ("2", "4"):
            t = tr[K][pair]
            d = t["dominant_transition"]
            cells += [f"{sn(d['from'], K)} → {sn(d['to'], K)} ({f(d['count'], 0)})", f(t["stability_rate"], 2),
                      f(t["masuk_tergenang"], 0)]
        rows.append(cells)
    L += table(["Pasangan level", "K = 2: transisi dominan", "K = 2: SR (%)", "K = 2: masuk Tergenang",
                "K = 4: transisi dominan", "K = 4: SR (%)", "K = 4: masuk Tergenang"], rows)
    L += ["", "Transisi dominan = sel matriks transisi terbesar di luar diagonal (perpindahan state). SR = stability "
          "rate pada grid non-Tergenang di kedua level.", ""]

    # (f)
    L += ["## (f) Riwayat keputusan K (kronologis)", "",
          "1. **Draft skripsi lama (sebelum rekonstruksi).** K = 6 dipilih dengan skor komposit I-Index, "
          "ketegasan partisi (di draft disebut CDVM), Dunn, DESC, dan PESC, mengikuti Guo dkk. (2015). Kode draft hilang; "
          "angkanya hanya tersimpan sebagai arsip (`docs/angka_draft_lama.json`).",
          "2. **Rekonstruksi v1 (`hasil-skripsi-v1`).** K dipilih dengan skor komposit (I-Index, Dunn, DESC, ketegasan "
          "partisi + parsimoni); terpilih K = 4 (model per level). Beberapa pilihan metrik saat itu dikalibrasi "
          "terhadap angka draft (CATATAN bagian A).",
          "3. **Putaran 2 (v2).** Desain diganti menjadi model data gabungan. Aturan stabilitas subsampel ditetapkan "
          "sebelum hasil v2 terlihat: K dengan rerata ARI subsampel tertinggi, pemecah seri K terkecil bila selisih "
          "≤ 0,01. Hasil: K = 2 (himpunan setara {2, 3}). Skor komposit hanya dilaporkan.",
          "4. **Putaran 3 (v3).** Stabilitas dihitung ulang pada data raster InaRisk: K = 2 (setara {2, 4}). Keluaran "
          "K = 2 dan 3.",
          "5. **Putaran 4 (v4).** Pemilihan K tidak dijalankan ulang (data identik v3); keluaran K = 2, 3, 4.",
          "6. **Putaran 5 (v5).** Peneliti menetapkan K utama = 4 dari himpunan setara {2, 4} setelah hasil v3/v4 "
          "terlihat, karena K = 4 memisahkan tipologi Terputus (METODOLOGI §9 (e)).",
          "7. **Putaran 6 (v6).** Koreksi snapping mengubah data; stabilitas dihitung ulang. Himpunan setara = {2}; "
          "K = 4 berselisih 0,0111 dan tidak lagi setara. Sesuai aturan, analisis berhenti sebelum ekspor dan keputusan "
          "dikembalikan ke peneliti (CATATAN P6-6).",
          "8. **Finalisasi v6.** Pada awal finalisasi sempat diusulkan kriteria berbasis indeks validitas (I-Index, "
          "Dunn, ketegasan partisi, mengikuti rancangan draft yang merujuk Guo dkk., 2015). Setelah diagnostik komponen "
          "I-Index dan validasi data buatan menunjukkan kelemahan I-Index dan Dunn, kriteria itu diganti: peneliti "
          "bersama pembimbing menetapkan **K utama = 4 atas dasar substantif** (bagian (g)). Keputusan ditetapkan "
          "**setelah semua hasil terlihat**, bukan direncanakan sejak awal rekonstruksi; METODOLOGI §9 (h) menggantikan "
          "semua butir keputusan K sebelumnya.", ""]

    # (g)
    fin_dir = PROJECT_ROOT / "output_bab4" / "finalisasi_v6"
    F = json.loads((fin_dir / "metrik_finalisasi_v6.json").read_text(encoding="utf-8")) \
        if (fin_dir / "metrik_finalisasi_v6.json").exists() else None
    S = json.loads((fin_dir / "validasi_sintetis.json").read_text(encoding="utf-8")) \
        if (fin_dir / "validasi_sintetis.json").exists() else None
    krit = kriteria_k_final(R, F, S)
    L += ["## (g) Keputusan final", ""]
    L += table(["Kriteria", "K yang ditunjuk", "Catatan keandalan"],
               [[r["Kriteria"], r["K yang ditunjuk"], r["Catatan keandalan"]] for r in krit])
    n2 = sum(r["K yang ditunjuk"] == 2 for r in krit)
    n4 = sum(r["K yang ditunjuk"] == 4 for r in krit)
    L += ["", f"Dari {len(krit)} kriteria, {n2} menunjuk K = 2 dan {n4} menunjuk K = 4; K = 4 **bukan** pilihan "
          "mayoritas metrik.", "",
          f"**Dasar substantif.** K = 4 dipilih karena memisahkan tipologi grid Terputus: {label_tipologi(p4['klaster'], 4)} berisi "
          f"{f(p4['jumlah_baris'], 0)} baris ({f(p4['persen_baris'], 2)} % data gabungan) dengan "
          f"{f(p4['proporsi_terputus'] * 100, 1)} % baris Terputus (waktu minimum = T_pen). Kelompok ini relevan bagi "
          "perencanaan evakuasi karena menandai grid yang tidak mencapai TES mana pun lewat jaringan jalan; pada "
          "K = 2 grid tersebut tercampur dalam tipologi terburuk yang berukuran 51,7 % data. Kesimpulan utama tidak "
          "bergantung pada K: perbandingan K = 4 vs K = 2 ada di `output_bab4/temuan_kunci.md` bagian (g) dan tabel S20. "
          "K = 2 dan K = 3 dilaporkan sebagai sensitivitas.", ""]
    DOC.write_text("\n".join(L), encoding="utf-8")
    print(f"ditulis: {DOC} (A3: K = 4 memisahkan Terputus = {pisah})")
    return pisah


if __name__ == "__main__":
    main()

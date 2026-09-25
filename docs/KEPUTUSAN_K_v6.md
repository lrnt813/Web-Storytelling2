# Keputusan K utama v6

Sumber: hasil terkunci `hasil-skripsi-v6` (`data/locked/`). Dokumen ini dibuat oleh `python -m scripts.keputusan_k_v6` dan tidak menjalankan klasterisasi ulang. **Keputusan: K utama = 4** (peneliti bersama pembimbing) atas **dasar substantif**; METODOLOGI §9 (h). Keputusan ditetapkan **setelah** semua hasil terlihat; ringkasannya di bagian (g), riwayatnya di bagian (f).

## (a) Tabel stabilitas K v6 (data gabungan)

10 subsampel 80 % id_grid; ARI inisialisasi = rerata 45 pasangan run seed 42–51.

| K | ARI subsampel (rerata) | ARI subsampel (sd) | ARI inisialisasi | Silhouette | Ketegasan partisi | Size entropy | Klaster terbesar (%) |
|---|---|---|---|---|---|---|---|
| 2 | 0,9593 | 0,0027 | 1,0000 | 0,243 | 0,341 | 0,693 | 51,7 |
| 3 | 0,9422 | 0,0074 | 0,9989 | 0,155 | 0,301 | 1,077 | 43,2 |
| 4 | 0,9481 | 0,0038 | 1,0000 | 0,201 | 0,457 | 1,153 | 39,0 |
| 5 | 0,9430 | 0,0045 | 1,0000 | 0,175 | 0,412 | 1,437 | 28,9 |
| 6 | 0,8149 | 0,1425 | 0,7757 | 0,160 | 0,376 | 1,654 | 24,8 |
| 7 | 0,9162 | 0,0181 | 0,9441 | 0,132 | 0,365 | 1,831 | 20,7 |
| 8 | 0,8993 | 0,0305 | 0,8879 | 0,130 | 0,354 | 1,981 | 18,4 |
| 9 | 0,7224 | 0,1558 | 0,7534 | 0,123 | 0,341 | 2,112 | 16,2 |
| 10 | 0,8124 | 0,1371 | 0,8112 | 0,102 | 0,334 | 2,228 | 14,6 |

## (b) Pemeriksaan adaptasi aturan one-standard-error

Aturan one-standard-error (Hastie, Tibshirani & Friedman, 2009, *The Elements of Statistical Learning*, ed. 2, hlm. 61 dan 244) memilih model paling sederhana yang berada dalam satu standard error dari model terbaik. Adaptasinya di sini: K terbaik = rerata ARI subsampel tertinggi (K = 2, 0,9593 ± 0,0027); tiap K dibandingkan dengan tiga ambang: toleransi 0,01 (aturan v2–v6), 1 sd K terbaik (0,0027), dan 1 SE = sd/√10 (0,0009).

| K | Selisih dari K terbaik | ≤ 0,01 | ≤ 1 sd | ≤ 1 SE |
|---|---|---|---|---|
| 2 | 0,0000 | Ya | Ya | Ya |
| 3 | 0,0171 | Tidak | Tidak | Tidak |
| 4 | 0,0111 | Tidak | Tidak | Tidak |
| 5 | 0,0163 | Tidak | Tidak | Tidak |
| 6 | 0,1444 | Tidak | Tidak | Tidak |
| 7 | 0,0431 | Tidak | Tidak | Tidak |
| 8 | 0,0599 | Tidak | Tidak | Tidak |
| 9 | 0,2368 | Tidak | Tidak | Tidak |
| 10 | 0,1468 | Tidak | Tidak | Tidak |

K = 4 berselisih 0,0111 dan tidak berada dalam ambang mana pun. Catatan: subsampel 80 % saling tumpang tindih (setiap pasang subsampel berbagi sebagian besar grid), sehingga nilai ARI antar-subsampel tidak saling bebas dan SE = sd/√B cenderung terlalu kecil; ambang 1 SE karena itu lebih ketat dari yang semestinya. Dengan ketiga ambang, stabilitas tetap menunjuk K = 2 saja.

## (c) K terbaik menurut setiap kriteria

| Kriteria | K terbaik | Nilai pada K terbaik | Nilai pada K = 4 |
|---|---|---|---|
| Stabilitas (ARI subsampel) | 2 | 0,9593 | 0,9481 |
| Silhouette | 2 | 0,2432 | 0,2007 |
| I-Index | 4 | 15,2182 | 15,2182 |
| Dunn | 5 | 0,0107 | 0,0105 |
| Ketegasan partisi | 4 | 0,4565 | 0,4565 |

I-Index dan ketegasan partisi menunjuk K = 4; Dunn menunjuk K = 5 dengan selisih sangat kecil dari K = 4 (0,0107 vs 0,0105; Dunn dihitung pada sampel 2.000 baris). Stabilitas dan Silhouette menunjuk K = 2.

### Pusat klaster K = 3 dan K = 4 dan komponen I-Index

Pusat fuzzy (bobot u^m, m = 1,7) di ruang PCA, dihitung dari keanggotaan terkunci (dibulatkan 6 desimal); kolom terakhir = rerata waktu minimum dan % baris bernilai penalti (T_pen) pada anggota klaster (label tegas).

**K = 3**

| Klaster | pc1 | pc2 | pc3 | pc4 | pc5 | Rerata waktu min. (menit) | % baris penalti |
|---|---|---|---|---|---|---|---|
| K0 (Tipologi 1) | -1,261 | -0,416 | 0,528 | 0,006 | -0,037 | 3,74 | 0,1 |
| K1 (Tipologi 2) | -0,012 | 0,054 | -0,154 | 0,070 | -0,041 | 6,66 | 0,2 |
| K2 (Tipologi 3) | 1,188 | 0,525 | -0,367 | -0,103 | 0,121 | 35,56 | 5,8 |

**K = 4**

| Klaster | pc1 | pc2 | pc3 | pc4 | pc5 | Rerata waktu min. (menit) | % baris penalti |
|---|---|---|---|---|---|---|---|
| K0 (Tipologi 1) | -1,425 | -0,374 | 0,636 | -0,029 | 0,034 | 3,60 | 0,0 |
| K1 (Tipologi 2) | -0,313 | -0,181 | -0,271 | 0,114 | -0,113 | 4,21 | 0,0 |
| K2 (Tipologi 3) | 0,726 | 0,612 | -0,314 | -0,092 | 0,140 | 11,66 | 0,1 |
| K3 (Tipologi 4) | 9,162 | -1,535 | 3,243 | 0,780 | -1,900 | 390,57 | 96,5 |

| K | E1 | EK | E1/EK | DK (jarak pusat terjauh) | Pasangan DK | I-Index (dihitung ulang) | I-Index (terkunci) |
|---|---|---|---|---|---|---|---|
| 2 | 156.711,7 | 133.888,0 | 1,170 | 1,912 | K0–K1 | 1,252 | 1,252 |
| 3 | 156.711,7 | 125.733,8 | 1,246 | 2,779 | K0–K2 | 1,333 | 1,333 |
| 4 | 156.711,7 | 112.115,2 | 1,398 | 11,164 | K0–K3 | 15,218 | 15,218 |

Lonjakan I-Index dari K = 3 ke K = 4 bertepatan dengan terbentuknya klaster baris bernilai penalti (Tipologi 4): DK naik tajam karena pusat klaster penalti jauh dari pusat lain, dan EK turun karena baris penalti yang beratribut hampir identik terkumpul pada satu pusat. Jadi I-Index pada K = 4 terutama mencerminkan pemisahan kelompok Terputus, bukan pemisahan yang merata di seluruh data.

## (d) Profil tipologi K = 2 dan K = 4 (v6)

| Model | Tipologi | Baris | % baris | Median waktu min. (menit) | P90 waktu min. (menit) | % baris penalti (waktu min.) | % Terputus |
|---|---|---|---|---|---|---|---|
| K = 2 | Tipologi 1 (terbaik) | 38.728 | 48,35 | 3,58 | 6,81 | 0,10 | 0,10 |
| K = 2 | Tipologi 2 (terburuk) | 41.375 | 51,65 | 8,70 | 18,91 | 3,20 | 3,20 |
| K = 4 | Tipologi 1 (terbaik) | 20.432 | 25,51 | 3,29 | 6,45 | 0,00 | 0,00 |
| K = 4 | Tipologi 2 | 27.019 | 33,73 | 4,16 | 6,83 | 0,00 | 0,00 |
| K = 4 | Tipologi 3 | 31.263 | 39,03 | 9,76 | 18,09 | 0,06 | 0,06 |
| K = 4 | Tipologi 4 (terburuk) | 1.389 | 1,73 | 403,29 | 403,29 | 96,54 | 96,54 |

**Tabel silang K = 2 × K = 4** (baris data gabungan; ARI antar-partisi 0,435):

| K = 2 \ K = 4 | Tipologi 1 | Tipologi 2 | Tipologi 3 | Tipologi 4 |
|---|---|---|---|---|
| Tipologi 1 | 20.432 | 17.706 | 552 | 38 |
| Tipologi 2 | 0 | 9.313 | 30.711 | 1.351 |

**Titik berhenti A3:** K = 4 v6 MASIH memisahkan tipologi Terputus. Tipologi 4 (terburuk) berisi 1.389 baris (1,73 %), dengan 96,5 % baris Terputus (waktu minimum = T_pen). Pada K = 2, baris Terputus tersebar dalam Tipologi 2 (3,2 % dari klaster itu).

## (e) Temuan utama K = 2 dan K = 4: transisi antarlevel

| Pasangan level | K = 2: transisi dominan | K = 2: SR (%) | K = 2: masuk Tergenang | K = 4: transisi dominan | K = 4: SR (%) | K = 4: masuk Tergenang |
|---|---|---|---|---|---|---|
| Baseline → Rendah | Tipologi 1 → Tipologi 2 (48) | 99,78 | 39 | Tipologi 1 → Tipologi 2 (61) | 99,49 | 39 |
| Rendah → Sedang | Tipologi 2 → Tergenang (1.956) | 92,38 | 3.336 | Tipologi 3 → Tergenang (1.870) | 87,08 | 3.336 |
| Sedang → Tinggi | Tipologi 1 → Tipologi 2 (2.638) | 82,88 | 3.800 | Tipologi 2 → Tipologi 3 (1.488) | 77,51 | 3.800 |
| Baseline → Tinggi | Tipologi 1 → Tergenang (4.121) | 77,09 | 7.175 | Tipologi 1 → Tergenang (2.845) | 71,18 | 7.175 |

Transisi dominan = sel matriks transisi terbesar di luar diagonal (perpindahan state). SR = stability rate pada grid non-Tergenang di kedua level.

## (f) Riwayat keputusan K (kronologis)

1. **Draft skripsi lama (sebelum rekonstruksi).** K = 6 dipilih dengan skor komposit I-Index, ketegasan partisi (di draft disebut CDVM), Dunn, DESC, dan PESC, mengikuti Guo dkk. (2015). Kode draft hilang; angkanya hanya tersimpan sebagai arsip (`docs/angka_draft_lama.json`).
2. **Rekonstruksi v1 (`hasil-skripsi-v1`).** K dipilih dengan skor komposit (I-Index, Dunn, DESC, ketegasan partisi + parsimoni); terpilih K = 4 (model per level). Beberapa pilihan metrik saat itu dikalibrasi terhadap angka draft (CATATAN bagian A).
3. **Putaran 2 (v2).** Desain diganti menjadi model data gabungan. Aturan stabilitas subsampel ditetapkan sebelum hasil v2 terlihat: K dengan rerata ARI subsampel tertinggi, pemecah seri K terkecil bila selisih ≤ 0,01. Hasil: K = 2 (himpunan setara {2, 3}). Skor komposit hanya dilaporkan.
4. **Putaran 3 (v3).** Stabilitas dihitung ulang pada data raster InaRisk: K = 2 (setara {2, 4}). Keluaran K = 2 dan 3.
5. **Putaran 4 (v4).** Pemilihan K tidak dijalankan ulang (data identik v3); keluaran K = 2, 3, 4.
6. **Putaran 5 (v5).** Peneliti menetapkan K utama = 4 dari himpunan setara {2, 4} setelah hasil v3/v4 terlihat, karena K = 4 memisahkan tipologi Terputus (METODOLOGI §9 (e)).
7. **Putaran 6 (v6).** Koreksi snapping mengubah data; stabilitas dihitung ulang. Himpunan setara = {2}; K = 4 berselisih 0,0111 dan tidak lagi setara. Sesuai aturan, analisis berhenti sebelum ekspor dan keputusan dikembalikan ke peneliti (CATATAN P6-6).
8. **Finalisasi v6.** Pada awal finalisasi sempat diusulkan kriteria berbasis indeks validitas (I-Index, Dunn, ketegasan partisi, mengikuti rancangan draft yang merujuk Guo dkk., 2015). Setelah diagnostik komponen I-Index dan validasi data buatan menunjukkan kelemahan I-Index dan Dunn, kriteria itu diganti: peneliti bersama pembimbing menetapkan **K utama = 4 atas dasar substantif** (bagian (g)). Keputusan ditetapkan **setelah semua hasil terlihat**, bukan direncanakan sejak awal rekonstruksi; METODOLOGI §9 (h) menggantikan semua butir keputusan K sebelumnya.

## (g) Keputusan final

| Kriteria | K yang ditunjuk | Catatan keandalan |
|---|---|---|
| Stabilitas subsampel (ARI) | 2 | Himpunan setara (selisih ≤ 0,01) = {2}; K = 4 berselisih 0,011 (juga di luar 1 sd dan 1 SE). |
| Silhouette | 2 | Tidak spasial; menilai pemisahan di ruang atribut. |
| Ketegasan partisi | 4 | Keanggotaan dihitung ulang di ruang atribut. |
| I-Index | 4 | Terdongkrak klaster baris penalti (DK 2,8 → 11,2 dari K = 3 ke K = 4); pada data buatan gagal menemukan K sebenarnya (tertinggi di K = 2, padahal K = 4). |
| Dunn | 5 | Tidak membedakan K = 4 dan K = 5 (0,0105 vs 0,0107; selisih jauh di bawah sd antarsampel ± 0,004). |
| DESC-N | 2 | Lulus validasi data buatan hanya lewat klausul "tidak monoton" (tertinggi di K = 2); memihak partisi kontigu. |
| PESC-N | 2 | Satu-satunya metrik yang memenuhi validasi data buatan secara penuh (tertinggi di K sebenarnya = 4); memihak partisi kontigu. |

Dari 7 kriteria, 4 menunjuk K = 2 dan 2 menunjuk K = 4; K = 4 **bukan** pilihan mayoritas metrik.

**Dasar substantif.** K = 4 dipilih karena memisahkan tipologi grid Terputus: Tipologi 4 (terburuk) berisi 1.389 baris (1,73 % data gabungan) dengan 96,5 % baris Terputus (waktu minimum = T_pen). Kelompok ini relevan bagi perencanaan evakuasi karena menandai grid yang tidak mencapai TES mana pun lewat jaringan jalan; pada K = 2 grid tersebut tercampur dalam tipologi terburuk yang berukuran 51,7 % data. Kesimpulan utama tidak bergantung pada K: perbandingan K = 4 vs K = 2 ada di `output_bab4/temuan_kunci.md` bagian (g) dan tabel S20. K = 2 dan K = 3 dilaporkan sebagai sensitivitas.

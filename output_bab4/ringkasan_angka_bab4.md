# Ringkasan angka kunci Bab IV

Sumber: `data/locked/` — commit analisis `1fdcec2ca57cadc3e03dc603b59f3259f2a6911c`, dikunci 2026-09-25T12:30:37+07:00. K utama = **4** (pengaturan_hasil.json); K lain = sensitivitas.

## Data dan level

- Grid 22.673; segmen jalan 162.608; TES 1.647; T_pen 403,29 menit
- Data gabungan 80.103 baris
- Baseline (tidak ada kelas ditutup): Tergenang 0 (0,00 %); ruas ditutup 0; TES valid 1.434; rerata waktu minimum 8,73 menit (median 5,69); TAS 68 (0,30 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 249 / 38; absolut v3 5.108; persentil 1.668; TES terdekat tidak terjangkau 157
  - Kategori akses (30 menit): Terjangkau 22.371 (98,67 %); Jauh 202 (0,89 %); Terputus 100 (0,44 %); Tergenang 0 (0,00 %)
- Level Rendah (kelas 3 ditutup): Tergenang 39 (0,17 %); ruas ditutup 710; TES valid 1.434; rerata waktu minimum 9,02 menit (median 5,69); TAS 76 (0,34 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 253 / 39; absolut v3 5.108; persentil 1.634; TES terdekat tidak terjangkau 171
  - Kategori akses (30 menit): Terjangkau 22.269 (98,22 %); Jauh 250 (1,10 %); Terputus 115 (0,51 %); Tergenang 39 (0,17 %)
  - TAS baru akibat banjir 8; TAS hilang 0 (jadi Tergenang 0, jadi TES terdekat tidak terjangkau 0, lainnya 0)
- Level Sedang (kelas ≥ 2 ditutup): Tergenang 3.375 (14,89 %); ruas ditutup 20.963; TES valid 1.367; rerata waktu minimum 16,59 menit (median 5,34); TAS 76 (0,39 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 210 / 37; absolut v3 4.507; persentil 1.338; TES terdekat tidak terjangkau 593
  - Kategori akses (30 menit): Terjangkau 18.732 (82,62 %); Jauh 61 (0,27 %); Terputus 505 (2,23 %); Tergenang 3.375 (14,89 %)
  - TAS baru akibat banjir 53; TAS hilang 45 (jadi Tergenang 36, jadi TES terdekat tidak terjangkau 6, lainnya 3)
- Level Tinggi (kelas ≥ 1 ditutup): Tergenang 7.175 (31,65 %); ruas ditutup 44.096; TES valid 989; rerata waktu minimum 24,00 menit (median 6,17); TAS 44 (0,28 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 203 / 16; absolut v3 3.288; persentil 964; TES terdekat tidak terjangkau 939
  - Kategori akses (30 menit): Terjangkau 14.544 (64,15 %); Jauh 314 (1,38 %); Terputus 640 (2,82 %); Tergenang 7.175 (31,65 %)
  - TAS baru akibat banjir 27; TAS hilang 51 (jadi Tergenang 41, jadi TES terdekat tidak terjangkau 7, lainnya 3)

## Pemilihan K

- K = 2: ARI subsampel 0,959 ± 0,003; ARI inisialisasi 1,000; Silhouette 0,243
- K = 3: ARI subsampel 0,942 ± 0,007; ARI inisialisasi 0,999; Silhouette 0,155
- K = 4: ARI subsampel 0,948 ± 0,004; ARI inisialisasi 1,000; Silhouette 0,201
- Aturan stabilitas (pemecah seri K terkecil) memilih K = 2; kandidat dalam toleransi: 2

## Model

### Model K = 4

- Validitas: Silhouette (sampel) 0,201, ketegasan partisi 0,457, PC 0,541, PE 0,793, klaster terbesar 39,03 %
- K0 — **Tipologi 1 (terbaik)**: 20.432 baris (25,51 %); waktu minimum median 3,29 [P75 4,82; P90 6,45] menit, rerata 3,60; > 30 menit 0,00 %; Terputus 0,00 %; terisolasi 0,000
- K1 — **Tipologi 2**: 27.019 baris (33,73 %); waktu minimum median 4,16 [P75 5,60; P90 6,83] menit, rerata 4,21; > 30 menit 0,00 %; Terputus 0,00 %; terisolasi 0,000
- K2 — **Tipologi 3**: 31.263 baris (39,03 %); waktu minimum median 9,76 [P75 13,05; P90 18,09] menit, rerata 11,66; > 30 menit 2,60 %; Terputus 0,06 %; terisolasi 0,001
- K3 — **Tipologi 4 (terburuk)**: 1.389 baris (1,73 %); waktu minimum median 403,29 [P75 403,29; P90 403,29] menit, rerata 390,57; > 30 menit 98,92 %; Terputus 96,54 %; terisolasi 0,965
- Baseline: K0 = 7.009 (30,91 %), K1 = 7.246 (31,96 %), K2 = 8.316 (36,68 %), K3 = 102 (0,45 %), Tergenang = 0 (0,00 %)
- Rendah: K0 = 6.945 (30,63 %), K1 = 7.275 (32,09 %), K2 = 8.297 (36,59 %), K3 = 117 (0,52 %), Tergenang = 39 (0,17 %)
- Sedang: K0 = 4.647 (20,50 %), K1 = 7.183 (31,68 %), K2 = 6.967 (30,73 %), K3 = 501 (2,21 %), Tergenang = 3.375 (14,89 %)
- Tinggi: K0 = 1.831 (8,08 %), K1 = 5.315 (23,44 %), K2 = 7.683 (33,89 %), K3 = 669 (2,95 %), Tergenang = 7.175 (31,65 %)
- Baseline → Rendah: masuk Tergenang 39; SR 99,49 %; ARI 0,986; dominan K0 → K1 (61); CDVM 0,004
- Rendah → Sedang: masuk Tergenang 3.336; SR 87,08 %; ARI 0,682; dominan K2 → Tergenang (1.870); CDVM 0,164
- Sedang → Tinggi: masuk Tergenang 3.800; SR 77,51 %; ARI 0,480; dominan K1 → K2 (1.488); CDVM 0,207
- Baseline → Tinggi: masuk Tergenang 7.175; SR 71,18 %; ARI 0,373; dominan K0 → Tergenang (2.845); CDVM 0,341
- Grid turun ke tipologi terburuk Sedang → Tinggi: 497
- FCM: Silhouette 0,211, CH 7.102,1, DB 1,302, Moran's I 0,808, PC 0,532, PE 0,874, klaster terbesar 31,14 %
- SFCM: Silhouette 0,165, CH 6.584,6, DB 1,453, Moran's I 0,833, PC 0,391, PE 1,114, klaster terbesar 27,89 %
- SDWFCM: Silhouette 0,205, CH 6.885,2, DB 1,297, Moran's I 0,847, PC 0,497, PE 0,933, klaster terbesar 30,40 %
- REDCAP: Silhouette 0,058, CH 229,5, DB 7,410, Moran's I 1,000, PC –, PE –, klaster terbesar 82,19 %
- SKATER: **gagal** — ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.

### Model K = 2

- Validitas: Silhouette (sampel) 0,243, ketegasan partisi 0,341, PC 0,685, PE 0,481, klaster terbesar 51,65 %
- K0 — **Tipologi 1 (terbaik)**: 38.728 baris (48,35 %); waktu minimum median 3,58 [P75 5,19; P90 6,81] menit, rerata 4,24; > 30 menit 0,10 %; Terputus 0,10 %; terisolasi 0,001
- K1 — **Tipologi 2 (terburuk)**: 41.375 baris (51,65 %); waktu minimum median 8,70 [P75 12,36; P90 18,91] menit, rerata 22,48; > 30 menit 5,19 %; Terputus 3,20 %; terisolasi 0,032
- Baseline: K0 = 12.313 (54,31 %), K1 = 10.360 (45,69 %), Tergenang = 0 (0,00 %)
- Rendah: K0 = 12.262 (54,08 %), K1 = 10.372 (45,75 %), Tergenang = 39 (0,17 %)
- Sedang: K0 = 9.479 (41,81 %), K1 = 9.819 (43,31 %), Tergenang = 3.375 (14,89 %)
- Tinggi: K0 = 4.674 (20,61 %), K1 = 10.824 (47,74 %), Tergenang = 7.175 (31,65 %)
- Baseline → Rendah: masuk Tergenang 39; SR 99,78 %; ARI 0,991; dominan K0 → K1 (48); CDVM 0,002
- Rendah → Sedang: masuk Tergenang 3.336; SR 92,38 %; ARI 0,718; dominan K1 → Tergenang (1.956); CDVM 0,147
- Sedang → Tinggi: masuk Tergenang 3.800; SR 82,88 %; ARI 0,432; dominan K0 → K1 (2.638); CDVM 0,212
- Baseline → Tinggi: masuk Tergenang 7.175; SR 77,09 %; ARI 0,293; dominan K0 → Tergenang (4.121); CDVM 0,337
- Grid turun ke tipologi terburuk Sedang → Tinggi: 2.638
- FCM: Silhouette 0,305, CH 10.468,0, DB 1,242, Moran's I 0,768, PC 0,741, PE 0,409, klaster terbesar 56,54 %
- SFCM: Silhouette 0,299, CH 10.298,1, DB 1,252, Moran's I 0,762, PC 0,637, PE 0,541, klaster terbesar 54,31 %
- SDWFCM: Silhouette 0,299, CH 10.166,3, DB 1,256, Moran's I 0,834, PC 0,717, PE 0,441, klaster terbesar 57,93 %
- REDCAP (**degeneratif**): Silhouette 0,172, CH 72,2, DB 8,075, Moran's I 1,000, PC –, PE –, klaster terbesar 94,40 %
- SKATER: **gagal** — ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.

### Model K = 3

- Validitas: Silhouette (sampel) 0,155, ketegasan partisi 0,301, PC 0,526, PE 0,801, klaster terbesar 43,21 %
- K0 — **Tipologi 1 (terbaik)**: 23.690 baris (29,57 %); waktu minimum median 3,12 [P75 4,57; P90 6,00] menit, rerata 3,74; > 30 menit 0,09 %; Terputus 0,09 %; terisolasi 0,001
- K1 — **Tipologi 2**: 34.612 baris (43,21 %); waktu minimum median 5,64 [P75 7,61; P90 9,47] menit, rerata 6,66; > 30 menit 0,22 %; Terputus 0,22 %; terisolasi 0,002
- K2 — **Tipologi 3 (terburuk)**: 21.801 baris (27,22 %); waktu minimum median 11,70 [P75 16,36; P90 28,94] menit, rerata 35,56; > 30 menit 9,59 %; Terputus 5,80 %; terisolasi 0,058
- Baseline: K0 = 7.883 (34,77 %), K1 = 9.942 (43,85 %), K2 = 4.848 (21,38 %), Tergenang = 0 (0,00 %)
- Rendah: K0 = 7.818 (34,48 %), K1 = 9.959 (43,92 %), K2 = 4.857 (21,42 %), Tergenang = 39 (0,17 %)
- Sedang: K0 = 5.616 (24,77 %), K1 = 8.790 (38,77 %), K2 = 4.892 (21,58 %), Tergenang = 3.375 (14,89 %)
- Tinggi: K0 = 2.373 (10,47 %), K1 = 5.921 (26,11 %), K2 = 7.204 (31,77 %), Tergenang = 7.175 (31,65 %)
- Baseline → Rendah: masuk Tergenang 39; SR 99,52 %; ARI 0,985; dominan K0 → K1 (61); CDVM 0,003
- Rendah → Sedang: masuk Tergenang 3.336; SR 86,79 %; ARI 0,640; dominan K2 → Tergenang (1.258); CDVM 0,149
- Sedang → Tinggi: masuk Tergenang 3.800; SR 70,19 %; ARI 0,317; dominan K1 → K2 (2.819); CDVM 0,270
- Baseline → Tinggi: masuk Tergenang 7.175; SR 62,41 %; ARI 0,222; dominan K1 → K2 (3.287); CDVM 0,420
- Grid turun ke tipologi terburuk Sedang → Tinggi: 3.352
- FCM: Silhouette 0,196, CH 7.690,4, DB 1,521, Moran's I 0,831, PC 0,585, PE 0,708, klaster terbesar 40,16 %
- SFCM: Silhouette 0,163, CH 7.346,1, DB 1,619, Moran's I 0,824, PC 0,474, PE 0,882, klaster terbesar 36,63 %
- SDWFCM: Silhouette 0,212, CH 7.463,1, DB 1,492, Moran's I 0,888, PC 0,564, PE 0,745, klaster terbesar 39,51 %
- REDCAP: Silhouette 0,076, CH 326,3, DB 6,879, Moran's I 1,000, PC –, PE –, klaster terbesar 82,19 %
- SKATER: **gagal** — ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.


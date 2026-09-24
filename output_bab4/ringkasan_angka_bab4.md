# Ringkasan angka kunci Bab IV

Sumber: `data/locked/` — commit analisis `01fe65b286723c3f24f5a1bf5afc2ea4fe2ded3d`, dikunci 2026-09-25T02:26:04+07:00. K utama = **4** (pengaturan_hasil.json); K lain = sensitivitas.

## Data dan level

- Grid 22.673; segmen jalan 162.608; TES 1.647; T_pen 403,87 menit
- Data gabungan 80.103 baris
- Baseline (tidak ada kelas ditutup): Tergenang 0 (0,00 %); ruas ditutup 0; TES valid 1.434; rerata waktu minimum 9,04 menit (median 5,81); TAS 62 (0,27 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 254 / 34; absolut v3 5.758; persentil 1.842; Terputus 168
  - Kategori akses (30 menit): Terjangkau 22.357 (98,61 %); Jauh 205 (0,90 %); Terputus 111 (0,49 %); Tergenang 0 (0,00 %)
- Level Rendah (kelas 3 ditutup): Tergenang 39 (0,17 %); ruas ditutup 710; TES valid 1.434; rerata waktu minimum 9,33 menit (median 5,80); TAS 70 (0,31 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 258 / 36; absolut v3 5.757; persentil 1.811; Terputus 182
  - Kategori akses (30 menit): Terjangkau 22.254 (98,15 %); Jauh 254 (1,12 %); Terputus 126 (0,56 %); Tergenang 39 (0,17 %)
  - TAS baru akibat banjir 8; TAS hilang 0 (jadi Tergenang 0, jadi Terputus 0, lainnya 0)
- Level Sedang (kelas ≥ 2 ditutup): Tergenang 3.375 (14,89 %); ruas ditutup 20.963; TES valid 1.367; rerata waktu minimum 16,67 menit (median 5,48); TAS 77 (0,40 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 218 / 37; absolut v3 5.092; persentil 1.485; Terputus 600
  - Kategori akses (30 menit): Terjangkau 18.732 (82,62 %); Jauh 64 (0,28 %); Terputus 502 (2,21 %); Tergenang 3.375 (14,89 %)
  - TAS baru akibat banjir 54; TAS hilang 39 (jadi Tergenang 31, jadi Terputus 7, lainnya 1)
- Level Tinggi (kelas ≥ 1 ditutup): Tergenang 7.175 (31,65 %); ruas ditutup 44.096; TES valid 989; rerata waktu minimum 24,41 menit (median 6,29); TAS 44 (0,28 % non-Tergenang); TAS ≥ 20 / ≥ 40 menit 209 / 16; absolut v3 3.685; persentil 1.047; Terputus 951
  - Kategori akses (30 menit): Terjangkau 14.529 (64,08 %); Jauh 318 (1,40 %); Terputus 651 (2,87 %); Tergenang 7.175 (31,65 %)
  - TAS baru akibat banjir 27; TAS hilang 45 (jadi Tergenang 35, jadi Terputus 8, lainnya 2)

## Pemilihan K

- K = 2: ARI subsampel 0,957 ± 0,004; ARI inisialisasi 1,000; Silhouette 0,243
- K = 3: ARI subsampel 0,940 ± 0,006; ARI inisialisasi 0,999; Silhouette 0,156
- K = 4: ARI subsampel 0,949 ± 0,003; ARI inisialisasi 1,000; Silhouette 0,203
- Aturan stabilitas (pemecah seri K terkecil) memilih K = 2; kandidat dalam toleransi: 2, 4

## Model

### Model K = 4

- Validitas: Silhouette (sampel) 0,203, ketegasan partisi 0,456, PC 0,542, PE 0,793, klaster terbesar 38,97 %
- K0 — **Tipologi 1 (terbaik)**: 20.397 baris (25,46 %); waktu minimum median 3,44 [P75 4,99; P90 6,61] menit, rerata 3,73; > 30 menit 0,00 %; Terputus 0,00 %; terisolasi 0,000
- K1 — **Tipologi 2**: 27.069 baris (33,79 %); waktu minimum median 4,28 [P75 5,72; P90 6,92] menit, rerata 4,31; > 30 menit 0,00 %; Terputus 0,00 %; terisolasi 0,000
- K2 — **Tipologi 3**: 31.215 baris (38,97 %); waktu minimum median 9,89 [P75 13,16; P90 18,23] menit, rerata 11,80; > 30 menit 2,65 %; Terputus 0,07 %; terisolasi 0,001
- K3 — **Tipologi 4 (terburuk)**: 1.422 baris (1,78 %); waktu minimum median 403,87 [P75 403,87; P90 403,87] menit, rerata 390,12; > 30 menit 98,80 %; Terputus 96,27 %; terisolasi 0,963
- Baseline: K0 = 7.009 (30,91 %), K1 = 7.237 (31,92 %), K2 = 8.314 (36,67 %), K3 = 113 (0,50 %), Tergenang = 0 (0,00 %)
- Rendah: K0 = 6.938 (30,60 %), K1 = 7.277 (32,10 %), K2 = 8.291 (36,57 %), K3 = 128 (0,56 %), Tergenang = 39 (0,17 %)
- Sedang: K0 = 4.639 (20,46 %), K1 = 7.196 (31,74 %), K2 = 6.966 (30,72 %), K3 = 497 (2,19 %), Tergenang = 3.375 (14,89 %)
- Tinggi: K0 = 1.811 (7,99 %), K1 = 5.359 (23,64 %), K2 = 7.644 (33,71 %), K3 = 684 (3,02 %), Tergenang = 7.175 (31,65 %)
- Baseline → Rendah: masuk Tergenang 39; SR 99,51 %; ARI 0,987; dominan K0 → K1 (66); CDVM 0,004
- Rendah → Sedang: masuk Tergenang 3.336; SR 87,31 %; ARI 0,687; dominan K2 → Tergenang (1.876); CDVM 0,163
- Sedang → Tinggi: masuk Tergenang 3.800; SR 77,51 %; ARI 0,480; dominan K1 → K2 (1.474); CDVM 0,206
- Baseline → Tinggi: masuk Tergenang 7.175; SR 71,33 %; ARI 0,376; dominan K0 → Tergenang (2.861); CDVM 0,342
- Grid turun ke tipologi terburuk Sedang → Tinggi: 510
- FCM: Silhouette 0,208, CH 6.953,0, DB 1,306, Moran's I 0,809, PC 0,531, PE 0,876, klaster terbesar 31,02 %
- SFCM: Silhouette 0,162, CH 6.418,8, DB 1,461, Moran's I 0,830, PC 0,390, PE 1,118, klaster terbesar 27,72 %
- SDWFCM: Silhouette 0,204, CH 6.735,0, DB 1,300, Moran's I 0,845, PC 0,497, PE 0,934, klaster terbesar 30,63 %
- REDCAP: Silhouette 0,002, CH 255,6, DB 4,977, Moran's I 1,000, PC –, PE –, klaster terbesar 89,35 %
- SKATER: **gagal** — ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.

### Model K = 2

- Validitas: Silhouette (sampel) 0,243, ketegasan partisi 0,340, PC 0,685, PE 0,482, klaster terbesar 51,13 %
- K0 — **Tipologi 1 (terbaik)**: 39.147 baris (48,87 %); waktu minimum median 3,72 [P75 5,34; P90 6,94] menit, rerata 4,31; > 30 menit 0,08 %; Terputus 0,08 %; terisolasi 0,001
- K1 — **Tipologi 2 (terburuk)**: 40.956 baris (51,13 %); waktu minimum median 8,87 [P75 12,55; P90 19,22] menit, rerata 23,13; > 30 menit 5,37 %; Terputus 3,31 %; terisolasi 0,033
- Baseline: K0 = 12.440 (54,87 %), K1 = 10.233 (45,13 %), Tergenang = 0 (0,00 %)
- Rendah: K0 = 12.389 (54,64 %), K1 = 10.245 (45,19 %), Tergenang = 39 (0,17 %)
- Sedang: K0 = 9.567 (42,20 %), K1 = 9.731 (42,92 %), Tergenang = 3.375 (14,89 %)
- Tinggi: K0 = 4.751 (20,95 %), K1 = 10.747 (47,40 %), Tergenang = 7.175 (31,65 %)
- Baseline → Rendah: masuk Tergenang 39; SR 99,78 %; ARI 0,991; dominan K0 → K1 (48); CDVM 0,002
- Rendah → Sedang: masuk Tergenang 3.336; SR 92,25 %; ARI 0,714; dominan K1 → Tergenang (1.951); CDVM 0,147
- Sedang → Tinggi: masuk Tergenang 3.800; SR 82,86 %; ARI 0,432; dominan K0 → K1 (2.641); CDVM 0,212
- Baseline → Tinggi: masuk Tergenang 7.175; SR 76,91 %; ARI 0,289; dominan K0 → Tergenang (4.144); CDVM 0,339
- Grid turun ke tipologi terburuk Sedang → Tinggi: 2.641
- FCM: Silhouette 0,303, CH 10.279,8, DB 1,247, Moran's I 0,769, PC 0,739, PE 0,411, klaster terbesar 56,15 %
- SFCM: Silhouette 0,295, CH 10.025,9, DB 1,261, Moran's I 0,760, PC 0,635, PE 0,544, klaster terbesar 54,11 %
- SDWFCM: Silhouette 0,296, CH 9.960,1, DB 1,262, Moran's I 0,835, PC 0,715, PE 0,443, klaster terbesar 57,68 %
- REDCAP (**degeneratif**): Silhouette 0,055, CH 202,0, DB 2,212, Moran's I 1,000, PC –, PE –, klaster terbesar 98,20 %
- SKATER: **gagal** — ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.

### Model K = 3

- Validitas: Silhouette (sampel) 0,156, ketegasan partisi 0,301, PC 0,526, PE 0,800, klaster terbesar 43,38 %
- K0 — **Tipologi 1 (terbaik)**: 23.669 baris (29,55 %); waktu minimum median 3,25 [P75 4,73; P90 6,16] menit, rerata 3,78; > 30 menit 0,07 %; Terputus 0,07 %; terisolasi 0,001
- K1 — **Tipologi 2**: 34.749 baris (43,38 %); waktu minimum median 5,75 [P75 7,73; P90 9,59] menit, rerata 6,72; > 30 menit 0,20 %; Terputus 0,20 %; terisolasi 0,002
- K2 — **Tipologi 3 (terburuk)**: 21.685 baris (27,07 %); waktu minimum median 11,86 [P75 16,53; P90 29,75] menit, rerata 36,57; > 30 menit 9,89 %; Terputus 6,01 %; terisolasi 0,060
- Baseline: K0 = 7.866 (34,69 %), K1 = 9.991 (44,07 %), K2 = 4.816 (21,24 %), Tergenang = 0 (0,00 %)
- Rendah: K0 = 7.797 (34,39 %), K1 = 10.013 (44,16 %), K2 = 4.824 (21,28 %), Tergenang = 39 (0,17 %)
- Sedang: K0 = 5.630 (24,83 %), K1 = 8.794 (38,79 %), K2 = 4.874 (21,50 %), Tergenang = 3.375 (14,89 %)
- Tinggi: K0 = 2.376 (10,48 %), K1 = 5.951 (26,25 %), K2 = 7.171 (31,63 %), Tergenang = 7.175 (31,65 %)
- Baseline → Rendah: masuk Tergenang 39; SR 99,51 %; ARI 0,985; dominan K0 → K1 (66); CDVM 0,003
- Rendah → Sedang: masuk Tergenang 3.336; SR 86,97 %; ARI 0,645; dominan K2 → Tergenang (1.260); CDVM 0,149
- Sedang → Tinggi: masuk Tergenang 3.800; SR 70,23 %; ARI 0,317; dominan K1 → K2 (2.810); CDVM 0,269
- Baseline → Tinggi: masuk Tergenang 7.175; SR 62,52 %; ARI 0,222; dominan K1 → K2 (3.280); CDVM 0,420
- Grid turun ke tipologi terburuk Sedang → Tinggi: 3.347
- FCM: Silhouette 0,194, CH 7.558,7, DB 1,524, Moran's I 0,831, PC 0,584, PE 0,710, klaster terbesar 40,25 %
- SFCM: Silhouette 0,161, CH 7.194,0, DB 1,622, Moran's I 0,821, PC 0,472, PE 0,885, klaster terbesar 36,35 %
- SDWFCM: Silhouette 0,209, CH 7.313,5, DB 1,498, Moran's I 0,888, PC 0,564, PE 0,746, klaster terbesar 39,22 %
- REDCAP (**degeneratif**): Silhouette 0,023, CH 180,1, DB 2,881, Moran's I 1,000, PC –, PE –, klaster terbesar 95,78 %
- SKATER: **gagal** — ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.


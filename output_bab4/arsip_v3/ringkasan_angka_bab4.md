# Ringkasan angka kunci Bab IV

Sumber: `data/locked/` — commit analisis `4413d4f0fa84d36e403817d49c2d2f34a508af0a`, dikunci 2026-09-24T21:53:53+07:00. K utama = **3** (pengaturan_hasil.json); K lain = sensitivitas.

## Data dan level

- Grid 22.673; segmen jalan 162.608; TES 1.647; T_pen 403,87 menit
- Data gabungan 80.103 baris
- Baseline (tidak ada kelas ditutup): Tergenang 0 (0,00 %); ruas ditutup 0; TES valid 1.434; rerata waktu minimum 9,04 menit (median 5,81); TAS 5.758 (25,40 % non-Tergenang); Terputus 168; TAS persentil 1.842
- Level Rendah (kelas 3 ditutup): Tergenang 39 (0,17 %); ruas ditutup 710; TES valid 1.434; rerata waktu minimum 9,33 menit (median 5,80); TAS 5.757 (25,44 % non-Tergenang); Terputus 182; TAS persentil 1.811
- Level Sedang (kelas ≥ 2 ditutup): Tergenang 3.375 (14,89 %); ruas ditutup 20.963; TES valid 1.367; rerata waktu minimum 16,67 menit (median 5,48); TAS 5.092 (26,39 % non-Tergenang); Terputus 600; TAS persentil 1.485
- Level Tinggi (kelas ≥ 1 ditutup): Tergenang 7.175 (31,65 %); ruas ditutup 44.096; TES valid 989; rerata waktu minimum 24,41 menit (median 6,29); TAS 3.685 (23,78 % non-Tergenang); Terputus 951; TAS persentil 1.047

## Pemilihan K

- K = 2: ARI subsampel 0,957 ± 0,004; ARI inisialisasi 1,000; Silhouette 0,243
- K = 3: ARI subsampel 0,940 ± 0,006; ARI inisialisasi 0,999; Silhouette 0,156
- Aturan stabilitas (pemecah seri K terkecil) memilih K = 2; kandidat dalam toleransi: 2, 4

## Model

### Model K = 3

- Validitas: Silhouette (sampel) 0,156, ketegasan partisi 0,301, PC 0,526, PE 0,800, klaster terbesar 43,38 %
- K0 — **Akses Baik**: 23.669 baris (29,55 %); waktu minimum median 3,25 [P25 2,00; P75 4,73] menit, rerata 3,78; penalti 0,07 %; terisolasi 0,001
- K1 — **Akses Baik**: 34.749 baris (43,38 %); waktu minimum median 5,75 [P25 3,88; P75 7,73] menit, rerata 6,72; penalti 0,20 %; terisolasi 0,002
- K2 — **Akses Sedang**: 21.685 baris (27,07 %); waktu minimum median 11,86 [P25 8,79; P75 16,53] menit, rerata 36,57; penalti 6,01 %; terisolasi 0,060
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

### Model K = 2

- Validitas: Silhouette (sampel) 0,243, ketegasan partisi 0,340, PC 0,685, PE 0,482, klaster terbesar 51,13 %
- K0 — **Akses Baik**: 39.147 baris (48,87 %); waktu minimum median 3,72 [P25 2,32; P75 5,34] menit, rerata 4,31; penalti 0,08 %; terisolasi 0,001
- K1 — **Akses Baik**: 40.956 baris (51,13 %); waktu minimum median 8,87 [P25 6,29; P75 12,55] menit, rerata 23,13; penalti 3,31 %; terisolasi 0,033
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


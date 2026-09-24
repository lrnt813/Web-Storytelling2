# Ringkasan angka kunci Bab IV

Sumber: `data/locked/` — commit analisis `b8b192eb1e4912be1a80f414e43a3d6f525baefd`, dikunci 2026-09-24T17:40:53+07:00. Semua angka dalam format Indonesia.

## Data

- Jumlah grid analisis: **22.673**
- Jumlah segmen jalan: **162.608**
- Jumlah TES: **1.647** (Pendidikan 548, Kesehatan 29, Pemerintahan 238, Tempat Ibadah 791, GOR/Gedung Serbaguna 41)
- Waktu penalti T_pen (3 × T_max Baseline): **403,87 menit**
- Data gabungan: **72.275 baris** (Baseline 22.673, Rendah 20.142, Sedang 14.828, Tinggi 14.632)

## Waktu tempuh Baseline (termasuk ruas snapping)

- Rata-rata waktu tempuh minimum: **9,04 menit**
- Median waktu tempuh minimum: **5,81 menit**
- Kuartil ketiga waktu tempuh minimum: **9,11 menit**

## Pra-pemrosesan (data gabungan)

- Fitur terpilih: **9 dari 9** (Road_Density_mean, waktu_tes_pendidikan, waktu_tes_kesehatan, waktu_tes_pemerintahan, waktu_tes_ibadah, waktu_tes_gor, waktu_tes_min, jumlah_opsi_rute, is_isolated)
- Komponen PCA: **4** (varians kumulatif **81,00 %**)

## Pemilihan K (stabilitas)

- K terpilih: **2** (rerata ARI subsampel 0,964 ± 0,006; ARI inisialisasi 0,999)
- Nilai tertinggi 0,964 pada K = 2; kandidat dalam toleransi 0,01: 2, 3
- Runner-up: K = 3 (ARI 0,963); selisih 0,001
- Sensitivitas skor komposit lama: +DESC → K = 3, −DESC → K = 3

## Perbandingan algoritma (Baseline)

- FCM: Silhouette 0,325, CH 11.876,012, DB 1,171, Moran's I 0,768, tetangga sama 0,885, klaster terbesar 56,75 %
- SFCM: Silhouette 0,317, CH 11.729,323, DB 1,178, Moran's I 0,783, tetangga sama 0,891, klaster terbesar 53,84 %
- SDWFCM: Silhouette 0,319, CH 11.502,236, DB 1,184, Moran's I 0,832, tetangga sama 0,917, klaster terbesar 58,52 %
- REDCAP — **degeneratif, tidak layak dibandingkan**: Silhouette 0,060, CH 209,478, DB 2,200, Moran's I 1,000, tetangga sama 1,000, klaster terbesar 98,20 %
- SKATER: **gagal** (ValueError: Islands must be larger than the quorum. If not, drop the small islands and solve for clusters in the remaining field.) — tidak layak dibandingkan

## Profil tipologi (data gabungan)

- K0: 42.701 baris (59,08 %), waktu minimum 4,88 menit, opsi rute 4,99 — Akses Baik · Bahaya Sedang
- K1: 29.574 baris (40,92 %), waktu minimum 41,83 menit, opsi rute 4,39 — Akses Kritis · Bahaya Rendah

## Per level

### Baseline (tidak ada kelas ditutup)

- Grid Tergenang: **0** (0,00 %)
- Ruas jalan ditutup: **0**; TES valid: **1.434**
- Rata-rata waktu tempuh minimum (non-Tergenang): **9,04 menit**
- TAS **1.842** (8,12 % grid non-Tergenang); Non-TAS 20.663; Terputus 168; Tergenang 0
- Rerata DI TAS / Non-TAS: **4,214 / 1,923**; TAS yang juga DI ≥ 2: 100,00 %
- Distribusi: K0 = 17.059 (75,24 %), K1 = 5.614 (24,76 %), Tergenang = 0 (0,00 %)

### Level Rendah (kelas 3 ditutup)

- Grid Tergenang: **2.531** (11,16 %)
- Ruas jalan ditutup: **702**; TES valid: **1.218**
- Rata-rata waktu tempuh minimum (non-Tergenang): **9,84 menit**
- TAS **1.652** (8,20 % grid non-Tergenang); Non-TAS 18.328; Terputus 162; Tergenang 2.531
- Rerata DI TAS / Non-TAS: **4,156 / 1,912**; TAS yang juga DI ≥ 2: 100,00 %
- Distribusi: K0 = 13.792 (60,83 %), K1 = 6.350 (28,01 %), Tergenang = 2.531 (11,16 %)

### Level Sedang (kelas ≥ 2 ditutup)

- Grid Tergenang: **7.845** (34,60 %)
- Ruas jalan ditutup: **20.871**; TES valid: **857**
- Rata-rata waktu tempuh minimum (non-Tergenang): **27,10 menit**
- TAS **1.042** (7,03 % grid non-Tergenang); Non-TAS 12.967; Terputus 819; Tergenang 7.845
- Rerata DI TAS / Non-TAS: **4,347 / 1,976**; TAS yang juga DI ≥ 2: 100,00 %
- Distribusi: K0 = 6.983 (30,80 %), K1 = 7.845 (34,60 %), Tergenang = 7.845 (34,60 %)

### Level Tinggi (kelas ≥ 1 ditutup)

- Grid Tergenang: **8.041** (35,47 %)
- Ruas jalan ditutup: **41.619**; TES valid: **849**
- Rata-rata waktu tempuh minimum (non-Tergenang): **43,77 menit**
- TAS **958** (6,55 % grid non-Tergenang); Non-TAS 12.098; Terputus 1.576; Tergenang 8.041
- Rerata DI TAS / Non-TAS: **4,873 / 2,053**; TAS yang juga DI ≥ 2: 100,00 %
- Distribusi: K0 = 4.867 (21,47 %), K1 = 9.765 (43,07 %), Tergenang = 8.041 (35,47 %)

## Transisi

- Baseline → Rendah: masuk Tergenang **2.531** (11,16 %); stability rate **93,33 %**, ARI **0,742** (grid non-Tergenang di kedua level); dominan K0 → Tergenang (1.934 grid, Tergenang); active edges 4; CDVM 0,144
- Rendah → Sedang: masuk Tergenang **5.314** (23,44 %); stability rate **79,74 %**, ARI **0,354** (grid non-Tergenang di kedua level); dominan K0 → Tergenang (3.809 grid, Tergenang); active edges 4; CDVM 0,300
- Sedang → Tinggi: masuk Tergenang **196** (0,86 %); stability rate **85,65 %**, ARI **0,508** (grid non-Tergenang di kedua level); dominan K0 → K1 (2.092 grid, tipologi lain); active edges 4; CDVM 0,093
- Baseline → Tinggi: masuk Tergenang **8.041** (35,47 %); stability rate **59,58 %**, ARI **0,012** (grid non-Tergenang di kedua level); dominan K0 → Tergenang (6.284 grid, Tergenang); active edges 4; CDVM 0,538

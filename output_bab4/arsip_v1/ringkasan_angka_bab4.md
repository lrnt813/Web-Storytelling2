# Ringkasan angka kunci Bab IV

Sumber: `data/locked/` — commit analisis `3d90975f8acdcdda1503970f52fb39f04b336da0`, dikunci 2026-09-24T12:23:34+07:00. Semua angka dalam format Indonesia.

## Data

- Jumlah grid analisis: **22.673**
- Jumlah segmen jalan: **162.608**
- Jumlah TES: **1.647** (Pendidikan 548, Kesehatan 29, Pemerintahan 238, Tempat Ibadah 791, GOR/Gedung Serbaguna 41)
- Waktu penalti T_pen (3 × T_max Baseline): **402,26 menit**

## Waktu tempuh Baseline

- Rata-rata waktu tempuh minimum: **8,16 menit**
- Median waktu tempuh minimum: **4,96 menit**
- Kuartil ketiga waktu tempuh minimum: **8,19 menit**

## Pra-pemrosesan

- Fitur terpilih: **10 dari 10** (Road_Density_mean, waktu_tes_pendidikan, waktu_tes_kesehatan, waktu_tes_pemerintahan, waktu_tes_ibadah, waktu_tes_gor, waktu_tes_min, jumlah_opsi_rute, is_isolated, banjir)
- Komponen PCA: **5** (varians kumulatif **85,19 %**)

## Pemilihan K

- K terpilih: **4** (skor komposit 0,706)
- Runner-up: K = 2 (skor 0,689); selisih skor **0,017**

## Perbandingan algoritma (Baseline)

- SDWFCM: Silhouette 0,163, CH 3.649,192, DB 1,478, Moran's I 0,857, proporsi tetangga sama 0,859, WCSS 90.436,053
- SFCM: Silhouette 0,052, CH 3.051,704, DB 2,432, Moran's I 0,871, proporsi tetangga sama 0,748, WCSS 95.529,780
- REDCAP: Silhouette -0,046, CH 131,199, DB 5,027, Moran's I 1,000, proporsi tetangga sama 1,000, WCSS 131.821,690
- SKATER: Silhouette 0,773, CH 221,919, DB 1,631, Moran's I 0,833, proporsi tetangga sama 1,000, WCSS 130.284,214

## Per level

### Baseline

- Grid terdampak: **0** (0,00 %)
- Ruas jalan ditutup: **0**; TES valid: **1.434**
- Rata-rata waktu tempuh minimum: **8,16 menit**
- Grid terisolasi: **111** (terdampak 0, tidak terdampak 111)
- TAS: **1.415** (6,24 % semua grid); Non-TAS 21.090; Terputus 168
- Rerata DI TAS / Non-TAS: **3,925 / 1,619**
- TAS dengan ambang absolut DI ≥ 2: 1.309
- Ukuran klaster: K0 = 4.686 (20,67 %), K1 = 5.359 (23,64 %), K2 = 6.902 (30,44 %), K3 = 5.726 (25,25 %)

### Rendah

- Grid terdampak: **2.531** (11,16 %)
- Ruas jalan ditutup: **702**; TES valid: **1.218**
- Rata-rata waktu tempuh minimum: **9,29 menit**
- Grid terisolasi: **126** (terdampak 17, tidak terdampak 109)
- TAS: **1.438** (6,34 % semua grid); Non-TAS 21.053; Terputus 182
- Rerata DI TAS / Non-TAS: **3,812 / 1,614**
- TAS dengan ambang absolut DI ≥ 2: 1.293
- Ukuran klaster: K0 = 4.774 (21,06 %), K1 = 5.742 (25,33 %), K2 = 6.563 (28,95 %), K3 = 5.594 (24,67 %)

### Sedang

- Grid terdampak: **7.845** (34,60 %)
- Ruas jalan ditutup: **20.871**; TES valid: **857**
- Rata-rata waktu tempuh minimum: **51,67 menit**
- Grid terisolasi: **2.412** (terdampak 1.709, tidak terdampak 703)
- TAS: **1.136** (5,01 % semua grid); Non-TAS 18.459; Terputus 3.078
- Rerata DI TAS / Non-TAS: **3,997 / 1,910**
- TAS dengan ambang absolut DI ≥ 2: 1.092
- Ukuran klaster: K0 = 8.881 (39,17 %), K1 = 805 (3,55 %), K2 = 10.598 (46,74 %), K3 = 2.389 (10,54 %)

### Tinggi

- Grid terdampak: **8.041** (35,47 %)
- Ruas jalan ditutup: **41.619**; TES valid: **849**
- Rata-rata waktu tempuh minimum: **105,70 menit**
- Grid terisolasi: **5.606** (terdampak 4.286, tidak terdampak 1.320)
- TAS: **935** (4,12 % semua grid); Non-TAS 15.422; Terputus 6.316
- Rerata DI TAS / Non-TAS: **4,548 / 1,887**
- TAS dengan ambang absolut DI ≥ 2: 890
- Ukuran klaster: K0 = 11.177 (49,30 %), K1 = 4.795 (21,15 %), K2 = 1.117 (4,93 %), K3 = 5.584 (24,63 %)

## Transisi

- Baseline → Rendah: stability rate **74,46 %**, ARI **0,453**, transisi dominan K0 → K2 (1.245 grid), active edges 11
- Rendah → Sedang: stability rate **39,12 %**, ARI **0,119**, transisi dominan K1 → K0 (3.791 grid), active edges 12
- Sedang → Tinggi: stability rate **43,01 %**, ARI **0,156**, transisi dominan K2 → K0 (4.518 grid), active edges 12

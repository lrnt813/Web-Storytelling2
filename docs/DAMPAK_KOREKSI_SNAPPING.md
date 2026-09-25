# Dampak koreksi snapping (v5 → v6)

v5 = `data/locked/arsip_v5/` (snapping ke **verteks** jalan terdekat); v6 = `data/locked/` (snapping ke **ruas** terdekat dengan simpul virtual; METODOLOGI §4, CATATAN P6-1). Semua aturan lain sama. Dibuat oleh `python -m scripts.dampak_koreksi_snapping`; angka dari hasil terkunci.
T_pen v5 = 403,87 menit; T_pen v6 = 403,29 menit (aturan sama: 3 × waktu maksimum valid di Baseline).

## 1. Nasib TAS v5 yang ditandai kesalahan snapping

Baris lembar v5 terisi yang teks Penyebab/Catatan-nya memuat "snapping": **24** (Baseline 20, Rendah 4). Di v6: masih TAS **21**, tidak lagi TAS **3** (Non-TAS 3).

| id_grid | Level | T_aktual v5 | DI v5 | Status v6 | T_aktual v6 | DI v6 |
|---|---|---|---|---|---|---|
| 11219 | Baseline | 31,18 | 8,94 | TAS | 31,53 | 9,05 |
| 14598 | Baseline | 51,32 | 82,11 | TAS | 51,32 | 82,11 |
| 16216 | Baseline | 35,02 | 11,30 | TAS | 35,02 | 11,30 |
| 16438 | Baseline | 46,66 | 16,90 | TAS | 46,69 | 16,91 |
| 17011 | Baseline | 126,76 | 37,00 | Non-TAS | 8,48 | 2,48 |
| 17227 | Baseline | 31,74 | 7,06 | TAS | 31,72 | 7,05 |
| 17290 | Baseline | 64,62 | 13,10 | TAS | 64,85 | 13,15 |
| 17409 | Baseline | 45,48 | 14,24 | TAS | 45,42 | 14,22 |
| 17432 | Baseline | 31,95 | 9,85 | TAS | 32,16 | 9,91 |
| 17558 | Baseline | 71,14 | 17,52 | TAS | 71,19 | 17,53 |
| 17663 | Baseline | 38,89 | 16,69 | TAS | 38,99 | 16,74 |
| 17845 | Baseline | 39,30 | 21,61 | TAS | 39,70 | 21,83 |
| 18284 | Baseline | 96,91 | 22,93 | TAS | 96,95 | 22,94 |
| 18583 | Baseline | 31,06 | 6,91 | TAS | 31,27 | 6,96 |
| 19702 | Baseline | 95,08 | 20,11 | TAS | 94,40 | 19,97 |
| 19779 | Baseline | 93,29 | 25,15 | TAS | 92,90 | 25,04 |
| 20081 | Baseline | 54,65 | 14,26 | TAS | 51,51 | 13,44 |
| 20950 | Baseline | 54,84 | 12,34 | TAS | 54,90 | 12,35 |
| 20989 | Baseline | 112,81 | 33,14 | TAS | 112,99 | 33,19 |
| 21421 | Baseline | 51,33 | 19,12 | TAS | 51,71 | 19,27 |
| 8895 | Rendah | 30,15 | 48,24 | Non-TAS | 0,63 | 1,01 |
| 11219 | Rendah | 31,18 | 8,94 | TAS | 31,53 | 9,05 |
| 14598 | Rendah | 51,32 | 82,11 | TAS | 51,32 | 82,11 |
| 16778 | Rendah | 32,68 | 11,15 | Non-TAS | 4,63 | 1,58 |

## 2. Grid 8895 dan 9632 (kasus "belum terjelaskan" di v5)

| id_grid | Level | Status v5 | T_aktual v5 | DI v5 | Status v6 | T_aktual v6 | DI v6 | T_ideal |
|---|---|---|---|---|---|---|---|---|
| 8895 | Baseline | TAS | 30,15 | 48,24 | Non-TAS | 0,63 | 1,01 | 0,62 |
| 8895 | Rendah | TAS | 30,15 | 48,24 | Non-TAS | 0,63 | 1,01 | 0,62 |
| 8895 | Sedang | TAS | 30,15 | 48,24 | Non-TAS | 0,63 | 1,01 | 0,62 |
| 8895 | Tinggi | TES terdekat tidak terjangkau | 403,87 | – | Non-TAS | 0,63 | 1,01 | 0,62 |
| 9632 | Baseline | TAS | 70,39 | 25,04 | Non-TAS | 3,47 | 1,23 | 2,81 |
| 9632 | Rendah | TAS | 83,63 | 29,75 | Non-TAS | 3,47 | 1,23 | 2,81 |
| 9632 | Sedang | Tergenang | 4,40 | – | Tergenang | 4,21 | – | 2,81 |
| 9632 | Tinggi | Tergenang | 403,87 | – | Tergenang | 403,29 | – | 6,88 |

## 3. Jarak snapping (centroid grid dan TES valid ke jaringan terbuka)

Median/P90 verteks dihitung atas semua titik (seperti v5); median/P90 ruas atas titik yang ter-snap ≤ 300 m.

| Level | Titik | n | Median verteks (m) | P90 verteks (m) | Median ruas (m) | P90 ruas (m) | Ter-snap ≤ 300 m verteks | Ter-snap ≤ 300 m ruas |
|---|---|---|---|---|---|---|---|---|
| Baseline | grid | 22673 | 35,34 | 91,36 | 27,79 | 84,47 | 22587 | 22598 |
| Baseline | TES valid | 1434 | 21,17 | 47,03 | 15,20 | 35,21 | 1434 | 1434 |
| Rendah | grid | 22673 | 35,37 | 91,54 | 27,85 | 84,72 | 22587 | 22598 |
| Rendah | TES valid | 1434 | 21,17 | 47,03 | 15,20 | 35,21 | 1434 | 1434 |
| Sedang | grid | 22673 | 41,75 | 164,23 | 32,76 | 114,55 | 21507 | 21512 |
| Sedang | TES valid | 1367 | 21,01 | 47,02 | 15,11 | 35,92 | 1367 | 1367 |
| Tinggi | grid | 22673 | 56,45 | 511,86 | 39,65 | 154,68 | 19193 | 19198 |
| Tinggi | TES valid | 989 | 20,35 | 50,08 | 15,18 | 40,22 | 989 | 989 |

## 4. Jumlah TAS, Terputus, dan Jauh per level

TAS = aturan utama; Terputus dan Jauh = kategori akses dengan batas 30 menit.

| Level | TAS v5 | TAS v6 | TES terdekat tidak terjangkau v5 | TES terdekat tidak terjangkau v6 | Terputus v5 | Terputus v6 | Jauh (30) v5 | Jauh (30) v6 |
|---|---|---|---|---|---|---|---|---|
| Baseline | 62 | 68 | 168 | 157 | 111 | 100 | 205 | 202 |
| Rendah | 70 | 76 | 182 | 171 | 126 | 115 | 254 | 250 |
| Sedang | 77 | 76 | 600 | 593 | 502 | 505 | 64 | 61 |
| Tinggi | 44 | 44 | 951 | 939 | 651 | 640 | 318 | 314 |

## 5. Waktu tempuh minimum per level (grid non-Tergenang, menit)

"Terjangkau" = waktu < T_pen versi masing-masing. Dari kolom `waktu_min_<level>` CSV grid terkunci (dibulatkan 3 desimal).

| Level | Median v5 | Median v6 | P90 v5 | P90 v6 | Median terjangkau v5 | Median terjangkau v6 | P90 terjangkau v5 | P90 terjangkau v6 |
|---|---|---|---|---|---|---|---|---|
| Baseline | 5,81 | 5,69 | 13,61 | 13,44 | 5,78 | 5,67 | 13,33 | 13,21 |
| Rendah | 5,80 | 5,69 | 13,64 | 13,44 | 5,77 | 5,66 | 13,30 | 13,20 |
| Sedang | 5,48 | 5,34 | 12,80 | 12,63 | 5,36 | 5,23 | 11,72 | 11,60 |
| Tinggi | 6,29 | 6,17 | 17,68 | 17,66 | 6,03 | 5,92 | 14,58 | 14,49 |

## 6. Peta sebelum/sesudah: 10 grid dengan perubahan T_aktual terbesar

Baseline; grid yang terjangkau di kedua versi; diurutkan menurut |T_aktual v6 − T_aktual v5|. Peta: `output_bab4/dampak_koreksi_snapping/peta_<id_grid>.png` (kiri v5, kanan v6).

| id_grid | T_aktual v5 | T_aktual v6 | Selisih (menit) | DI v5 | DI v6 | Status v5 | Status v6 |
|---|---|---|---|---|---|---|---|
| 20764 | 125,51 | 6,93 | -118,57 | 27,70 | 1,53 | TAS | Non-TAS |
| 17011 | 126,76 | 8,48 | -118,27 | 37,00 | 2,48 | TAS | Non-TAS |
| 21538 | 16,99 | 126,63 | 109,64 | 1,69 | 12,60 | Non-TAS | Non-TAS |
| 15246 | 136,50 | 27,82 | -108,69 | 13,04 | 2,66 | Non-TAS | Non-TAS |
| 21663 | 9,40 | 116,89 | 107,49 | 2,54 | 31,60 | Non-TAS | TAS |
| 12942 | 32,26 | 136,19 | 103,93 | 3,22 | 13,61 | Non-TAS | Non-TAS |
| 18133 | 7,85 | 110,39 | 102,53 | 1,52 | 21,43 | Non-TAS | Non-TAS |
| 15236 | 44,66 | 119,94 | 75,27 | 3,52 | 9,44 | Non-TAS | Non-TAS |
| 9632 | 70,39 | 3,47 | -66,92 | 25,04 | 1,23 | TAS | Non-TAS |
| 1198 | 4,77 | 67,50 | 62,72 | 1,66 | 23,43 | Non-TAS | TAS |

- `output_bab4/dampak_koreksi_snapping/peta_20764.png`
- `output_bab4/dampak_koreksi_snapping/peta_17011.png`
- `output_bab4/dampak_koreksi_snapping/peta_21538.png`
- `output_bab4/dampak_koreksi_snapping/peta_15246.png`
- `output_bab4/dampak_koreksi_snapping/peta_21663.png`
- `output_bab4/dampak_koreksi_snapping/peta_12942.png`
- `output_bab4/dampak_koreksi_snapping/peta_18133.png`
- `output_bab4/dampak_koreksi_snapping/peta_15236.png`
- `output_bab4/dampak_koreksi_snapping/peta_9632.png`
- `output_bab4/dampak_koreksi_snapping/peta_1198.png`

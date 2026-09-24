# Perbandingan angka draft lama vs hasil final

Bantuan revisi teks. Angka draft berasal dari `docs/angka_draft_lama.json`; angka final dari `data/locked/`. **Angka final yang berlaku.** Perbedaan mencerminkan koreksi metode (lihat docs/CATATAN_TEMUAN.md dan docs/METODOLOGI.md), bukan galat pembulatan.

## Tabel 9 — statistik waktu tempuh Baseline (menit)

| Variabel | Statistik | Draft | Final |
|---|---|---:|---:|
| waktu_tes_pendidikan | mean | 11,56 | 11,56 |
| waktu_tes_pendidikan | std | 28,51 | 28,51 |
| waktu_tes_pendidikan | min | 0,00 | 0,00 |
| waktu_tes_pendidikan | q25 | 4,89 | 4,89 |
| waktu_tes_pendidikan | median | 8,35 | 8,35 |
| waktu_tes_pendidikan | q75 | 12,77 | 12,76 |
| waktu_tes_pendidikan | max | 402,26 | 402,26 |
| waktu_tes_kesehatan | mean | 34,74 | 34,74 |
| waktu_tes_kesehatan | std | 36,23 | 36,23 |
| waktu_tes_kesehatan | min | 0,00 | 0,00 |
| waktu_tes_kesehatan | q25 | 19,12 | 19,12 |
| waktu_tes_kesehatan | median | 30,22 | 30,22 |
| waktu_tes_kesehatan | q75 | 42,82 | 42,82 |
| waktu_tes_kesehatan | max | 402,26 | 402,26 |
| waktu_tes_pemerintahan | mean | 21,64 | 21,64 |
| waktu_tes_pemerintahan | std | 35,11 | 35,11 |
| waktu_tes_pemerintahan | min | 0,00 | 0,00 |
| waktu_tes_pemerintahan | q25 | 9,80 | 9,80 |
| waktu_tes_pemerintahan | median | 17,05 | 17,05 |
| waktu_tes_pemerintahan | q75 | 25,85 | 25,85 |
| waktu_tes_pemerintahan | max | 402,26 | 402,26 |
| waktu_tes_ibadah | mean | 9,78 | 9,78 |
| waktu_tes_ibadah | std | 28,21 | 28,21 |
| waktu_tes_ibadah | min | 0,00 | 0,00 |
| waktu_tes_ibadah | q25 | 3,74 | 3,74 |
| waktu_tes_ibadah | median | 6,56 | 6,56 |
| waktu_tes_ibadah | q75 | 10,42 | 10,42 |
| waktu_tes_ibadah | max | 402,26 | 402,26 |
| waktu_tes_gor | mean | 39,06 | 39,06 |
| waktu_tes_gor | std | 38,60 | 38,60 |
| waktu_tes_gor | min | 0,00 | 0,00 |
| waktu_tes_gor | q25 | 19,22 | 19,21 |
| waktu_tes_gor | median | 33,35 | 33,35 |
| waktu_tes_gor | q75 | 49,57 | 49,57 |
| waktu_tes_gor | max | 402,26 | 402,26 |
| waktu_tes_min | mean | 8,16 | 8,16 |
| waktu_tes_min | std | 28,19 | 28,19 |
| waktu_tes_min | min | 0,00 | 0,00 |
| waktu_tes_min | q25 | 2,68 | 2,68 |
| waktu_tes_min | median | 4,96 | 4,96 |
| waktu_tes_min | q75 | 8,19 | 8,19 |
| waktu_tes_min | max | 402,26 | 402,26 |

## Tabel 10 — kandidat K

K terpilih: draft **6**, final **4**.

| K | I-Index draft | I-Index final | Ketegasan (draft 'CDVM') | Ketegasan final | Dunn draft | Dunn final | DESC draft | DESC final |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1,723 | 1,312 | 0,610 | 0,351 | 0,023 | 0,001 | 0,153 | 0,139 |
| 3 | 1,726 | 1,200 | 0,632 | 0,306 | 0,014 | 0,001 | 0,648 | 0,203 |
| 4 | 2,015 | 1,168 | 0,663 | 0,309 | 0,005 | 0,001 | 0,352 | 7,480 |
| 5 | 1,708 | 0,959 | 0,678 | 0,296 | 0,006 | 0,003 | 0,851 | 0,466 |
| 6 | 1,737 | 0,865 | 0,694 | 0,302 | 0,014 | 0,001 | 28,987 | 4,489 |
| 7 | 1,465 | 0,776 | 0,698 | 0,298 | 0,012 | 0,001 | 35,006 | 0,858 |
| 8 | 1,339 | 0,810 | 0,706 | 0,306 | 0,001 | 0,003 | 45,825 | 1,530 |
| 9 | 1,226 | 0,761 | 0,710 | 0,306 | 0,007 | 0,002 | 48,911 | 8,601 |
| 10 | 1,099 | 0,674 | 0,714 | 0,300 | 0,011 | 0,002 | 100,109 | 2,331 |

## Tabel 11 — perbandingan algoritma

| Algoritma | Metrik | Draft | Final |
|---|---|---:|---:|
| SDWFCM | silhouette | 0,210 | 0,163 |
| SDWFCM | calinski_harabasz | 6.894,000 | 3.649,192 |
| SDWFCM | davies_bouldin | 1,334 | 1,478 |
| SDWFCM | moran_i | 0,782 | 0,857 |
| SDWFCM | size_entropy | 1,710 | 1,376 |
| SDWFCM | wcss | 31.102,917 | 90.436,053 |
| SFCM | silhouette | 0,198 | 0,052 |
| SFCM | calinski_harabasz | 6.788,000 | 3.051,704 |
| SFCM | davies_bouldin | 1,421 | 2,432 |
| SFCM | moran_i | 0,758 | 0,871 |
| SFCM | size_entropy | 1,727 | 1,352 |
| SFCM | wcss | 31.265,781 | 95.529,780 |
| REDCAP | silhouette | -0,113 | -0,046 |
| REDCAP | calinski_harabasz | 154,200 | 131,199 |
| REDCAP | davies_bouldin | 7,592 | 5,027 |
| REDCAP | moran_i | 1,000 | 1,000 |
| REDCAP | size_entropy | 0,726 | 0,439 |
| REDCAP | wcss | 75.510,865 | 131.821,690 |
| SKATER | silhouette | 0,035 | 0,773 |
| SKATER | calinski_harabasz | 140,700 | 221,919 |
| SKATER | davies_bouldin | 2,106 | 1,631 |
| SKATER | moran_i | 0,973 | 0,833 |
| SKATER | size_entropy | 0,352 | 0,006 |
| SKATER | wcss | 75.729,606 | 130.284,214 |

## Tabel 12–15 — ukuran klaster

Nomor klaster draft bersifat arbitrer sehingga tidak dipasangkan satu-satu; yang dibandingkan adalah sebaran ukuran klaster (diurutkan dari terbesar).

| Level | Draft (terurut) | Final (terurut) |
|---|---|---|
| Baseline | 5.480, 5.377, 4.362, 3.060, 3.037, 1.357 | 6.902, 5.726, 5.359, 4.686 |
| Rendah | 5.236, 4.640, 4.402, 3.678, 3.043, 1.674 | 6.563, 5.742, 5.594, 4.774 |
| Sedang | 6.528, 4.423, 4.369, 3.311, 2.473, 1.569 | 10.598, 8.881, 2.389, 805 |
| Tinggi | 4.591, 4.274, 4.027, 3.858, 3.455, 2.468 | 11.177, 5.584, 4.795, 1.117 |

## Transisi

| Transisi | SR draft (%) | SR final (%) | ARI draft | ARI final |
|---|---:|---:|---:|---:|
| Baseline → Rendah | 47 | 74,46 | 0,57 | 0,453 |
| Rendah → Sedang | 11 | 39,12 | 0,27 | 0,119 |
| Sedang → Tinggi | 52 | 43,01 | 0,22 | 0,156 |

## Tabel 16 — Titik Aman Semu

Definisi final berbeda: grid Terputus dikeluarkan, persentil dari grid terjangkau, jarak minimum 50 m.

| Level | TAS draft | TAS final | % draft | % final | DI TAS draft | DI TAS final | DI Non-TAS draft | DI Non-TAS final | Terputus final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 1.460 | 1.415 | 6,44 | 6,24 | 4,99 | 3,925 | 2,05 | 1,619 | 168 |
| Rendah | 1.486 | 1.438 | 6,55 | 6,34 | 5,09 | 3,812 | 2,04 | 1,614 | 182 |
| Sedang | 726 | 1.136 | 3,20 | 5,01 | 11,01 | 3,997 | 5,79 | 1,910 | 3.078 |
| Tinggi | 265 | 935 | 1,17 | 4,12 | 200,20 | 4,548 | 11,34 | 1,887 | 6.316 |


# Temuan kunci Bab IV

Sumber: `data/locked/` (hasil-skripsi-v5). K utama = 4. Setiap angka menyebut tabel sumbernya di `output_bab4/`. Format angka Indonesia.

## (a) Kategori akses per level, batas 30 menit

Sumber: `T18` (Kategori akses per level (padanan Li dkk. 2026) untuk batas 20/30/40 menit).

| Level | Terjangkau | Jauh | Terputus | Tergenang |
|---|---:|---:|---:|---:|
| Baseline | 22.357 (98,61 %) | 205 (0,90 %) | 111 (0,49 %) | 0 (0,00 %) |
| Rendah | 22.254 (98,15 %) | 254 (1,12 %) | 126 (0,56 %) | 39 (0,17 %) |
| Sedang | 18.732 (82,62 %) | 64 (0,28 %) | 502 (2,21 %) | 3.375 (14,89 %) |
| Tinggi | 14.529 (64,08 %) | 318 (1,40 %) | 651 (2,87 %) | 7.175 (31,65 %) |

## (b) Grid Terjangkau di Baseline yang menjadi Terputus tanpa tergenang

- Baseline → Sedang: **360 grid** (sumber: `T19e` (Transisi kategori akses Baseline → Sedang (batas 30 menit; jumlah grid)), sel Terjangkau → Terputus).
- Baseline → Tinggi: **555 grid** (sumber: `T19d` (Transisi kategori akses Baseline → Tinggi (batas 30 menit; jumlah grid)), sel Terjangkau → Terputus).
- Kategori Terputus = non-Tergenang yang tidak mencapai TES mana pun; grid ini sendiri tidak tergenang, tetapi aksesnya terputus karena ruas jalan tertutup.

## (c) Profil tipologi K = 4

Sumber: `T07` (Profil tipologi SDWFCM K4 (data gabungan keempat level)) dan `T07b` (Waktu tempuh per kategori TES per klaster K4 (menit)).

| Tipologi | Baris (%) | Median / P75 / P90 waktu min. (menit) | > 30 menit | Terputus | Terisolasi | Kepadatan jalan | Kelas bahaya |
|---|---:|---|---:|---:|---:|---:|---:|
| Tipologi 1 (terbaik) | 20.397 (25,5 %) | 3,44 / 4,99 / 6,61 | 0,00 % | 0,00 % | 0,000 | 0,975 | 0,434 |
| Tipologi 2 | 27.069 (33,8 %) | 4,28 / 5,72 / 6,92 | 0,00 % | 0,00 % | 0,000 | 0,705 | 0,193 |
| Tipologi 3 | 31.215 (39,0 %) | 9,89 / 13,16 / 18,23 | 2,65 % | 0,07 % | 0,001 | 0,692 | 0,330 |
| Tipologi 4 (terburuk) | 1.422 (1,8 %) | 403,87 / 403,87 / 403,87 | 98,80 % | 96,27 % | 0,963 | 0,617 | 0,343 |

**Pembeda Tipologi 1 vs Tipologi 2** (sumber: `T07` (Profil tipologi SDWFCM K4 (data gabungan keempat level))): waktu tempuh minimum hampir sama (median 3,44 vs 4,28 menit). Pembedanya kepadatan jalan (rerata 0,975 vs 0,705) dan kelas bahaya deskriptif (rerata 0,434 vs 0,193; bukan fitur klasterisasi). Pada kategori TES tertentu (sumber: `T07b` (Waktu tempuh per kategori TES per klaster K4 (menit))) median waktu ke TES kesehatan 18,24 vs 37,55 menit, dan ke GOR 18,45 vs 39,29 menit.

## (d) Titik Aman Semu (aturan utama: DI ≥ 2, T_ideal ≤ 5 menit, T_aktual ≥ 30 menit)

Sumber: `T11` (Titik Aman Semu per level (aturan utama: DI ≥ 2, T_ideal ≤ 5 menit, T_aktual ≥ 30 menit)), `T11b` (Sensitivitas TAS: ambang T_aktual 20/40 menit, aturan absolut v3, aturan persentil), `T11e` (Perubahan TAS terhadap Baseline (aturan utama)).

| Level | TAS | % non-Tergenang | TAS baru akibat banjir | TAS hilang (jadi Tergenang / TES terdekat tidak terjangkau / lainnya) |
|---|---:|---:|---:|---|
| Baseline | 62 | 0,27 % | – | – |
| Rendah | 70 | 0,31 % | 8 | 0 (0 / 0 / 0) |
| Sedang | 77 | 0,40 % | 54 | 39 (31 / 7 / 1) |
| Tinggi | 44 | 0,28 % | 27 | 45 (35 / 8 / 2) |

## (e) Perbandingan algoritma di Baseline (K = 4)

Sumber: `T06` (Perbandingan algoritma pada Baseline K4).

| Algoritma | Status | Silhouette | CH | DB | Moran's I | PC | PE | Klaster terbesar | Catatan |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| FCM | ok | 0,208 | 6.953,0 | 1,306 | 0,809 | 0,531 | 0,876 | 31,0 % |  |
| SFCM | ok | 0,162 | 6.418,8 | 1,461 | 0,830 | 0,390 | 1,118 | 27,7 % |  |
| SDWFCM | ok | 0,204 | 6.735,0 | 1,300 | 0,845 | 0,497 | 0,934 | 30,6 % |  |
| REDCAP | ok | 0,002 | 255,6 | 4,977 | 1,000 | – | – | 89,3 % | nyaris degeneratif (klaster terbesar 89,3%; batas 90%) |
| SKATER | gagal | – | – | – | – | – | – | – % | gagal dijalankan; tidak layak dibandingkan |

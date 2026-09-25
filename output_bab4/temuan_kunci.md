# Temuan kunci Bab IV

Sumber: `data/locked/` (hasil-skripsi-v6). K utama = 4. Setiap angka menyebut tabel sumbernya di `output_bab4/`. Format angka Indonesia.

## (a) Kategori akses per level, batas 30 menit

Sumber: `T18` (Kategori akses per level (padanan Li dkk. 2026) untuk batas 20/30/40 menit).

| Level | Terjangkau | Jauh | Terputus | Tergenang |
|---|---:|---:|---:|---:|
| Baseline | 22.371 (98,67 %) | 202 (0,89 %) | 100 (0,44 %) | 0 (0,00 %) |
| Rendah | 22.269 (98,22 %) | 250 (1,10 %) | 115 (0,51 %) | 39 (0,17 %) |
| Sedang | 18.732 (82,62 %) | 61 (0,27 %) | 505 (2,23 %) | 3.375 (14,89 %) |
| Tinggi | 14.544 (64,15 %) | 314 (1,38 %) | 640 (2,82 %) | 7.175 (31,65 %) |

## (b) Grid Terjangkau di Baseline yang menjadi Terputus tanpa tergenang

- Baseline → Sedang: **375 grid** (sumber: `T19e` (Transisi kategori akses Baseline → Sedang (batas 30 menit; jumlah grid)), sel Terjangkau → Terputus).
- Baseline → Tinggi: **553 grid** (sumber: `T19d` (Transisi kategori akses Baseline → Tinggi (batas 30 menit; jumlah grid)), sel Terjangkau → Terputus).
- Kategori Terputus = non-Tergenang yang tidak mencapai TES mana pun; grid ini sendiri tidak tergenang, tetapi aksesnya terputus karena ruas jalan tertutup.

## (c) Profil tipologi K = 4

Sumber: `T07` (Profil tipologi SDWFCM K4 (data gabungan keempat level)) dan `T07b` (Waktu tempuh per kategori TES per klaster K4 (menit)).

| Tipologi | Baris (%) | Median / P75 / P90 waktu min. (menit) | > 30 menit | Terputus | Terisolasi | Kepadatan jalan | Kelas bahaya |
|---|---:|---|---:|---:|---:|---:|---:|
| Tipologi 1 (terbaik) | 20.432 (25,5 %) | 3,29 / 4,82 / 6,45 | 0,00 % | 0,00 % | 0,000 | 0,972 | 0,431 |
| Tipologi 2 | 27.019 (33,7 %) | 4,16 / 5,60 / 6,83 | 0,00 % | 0,00 % | 0,000 | 0,707 | 0,197 |
| Tipologi 3 | 31.263 (39,0 %) | 9,76 / 13,05 / 18,09 | 2,60 % | 0,06 % | 0,001 | 0,691 | 0,328 |
| Tipologi 4 (terburuk) | 1.389 (1,7 %) | 403,29 / 403,29 / 403,29 | 98,92 % | 96,54 % | 0,965 | 0,620 | 0,353 |

**Pembeda Tipologi 1 vs Tipologi 2** (sumber: `T07` (Profil tipologi SDWFCM K4 (data gabungan keempat level))): waktu tempuh minimum hampir sama (median 3,29 vs 4,16 menit). Pembedanya kepadatan jalan (rerata 0,972 vs 0,707) dan kelas bahaya deskriptif (rerata 0,431 vs 0,197; bukan fitur klasterisasi). Pada kategori TES tertentu (sumber: `T07b` (Waktu tempuh per kategori TES per klaster K4 (menit))) median waktu ke TES kesehatan 18,07 vs 37,44 menit, dan ke GOR 18,29 vs 39,15 menit.

## (d) Titik Aman Semu (aturan utama: DI ≥ 2, T_ideal ≤ 5 menit, T_aktual ≥ 30 menit)

Sumber: `T11` (Titik Aman Semu per level (aturan utama: DI ≥ 2, T_ideal ≤ 5 menit, T_aktual ≥ 30 menit)), `T11b` (Sensitivitas TAS: ambang T_aktual 20/40 menit, aturan absolut v3, aturan persentil), `T11e` (Perubahan TAS terhadap Baseline (aturan utama)).

| Level | TAS | % non-Tergenang | TAS baru akibat banjir | TAS hilang (jadi Tergenang / TES terdekat tidak terjangkau / lainnya) |
|---|---:|---:|---:|---|
| Baseline | 68 | 0,30 % | – | – |
| Rendah | 76 | 0,34 % | 8 | 0 (0 / 0 / 0) |
| Sedang | 76 | 0,39 % | 53 | 45 (36 / 6 / 3) |
| Tinggi | 44 | 0,28 % | 27 | 51 (41 / 7 / 3) |

## (e) Perbandingan algoritma di Baseline (K = 4)

Sumber: `T06` (Perbandingan algoritma pada Baseline K4 (termasuk SDWFCM versi asli Guo dkk., 2015)).

| Algoritma | Status | Silhouette | CH | DB | Moran's I | PC | PE | Klaster terbesar | Catatan |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| FCM | ok | 0,211 | 7.102,1 | 1,302 | 0,808 | 0,532 | 0,874 | 31,1 % |  |
| SFCM | ok | 0,165 | 6.584,6 | 1,453 | 0,833 | 0,391 | 1,114 | 27,9 % |  |
| SDWFCM | ok | 0,205 | 6.885,2 | 1,297 | 0,847 | 0,497 | 0,933 | 30,4 % |  |
| REDCAP | ok | 0,058 | 229,5 | 7,410 | 1,000 | – | – | 82,2 % |  |
| SKATER | gagal | – | – | – | – | – | – | – % | gagal dijalankan; tidak layak dibandingkan |

## (f) Atribusi banjir pada TAS

Sumber: `T11f` (Atribusi pengaruh banjir pada TAS (Rendah, Sedang, Tinggi)).

| Level | TAS | Dipicu banjir | Diperparah banjir | Tidak berubah | Lainnya | Median waktu Baseline (dipicu) | Median tambahan (dipicu) | Median tambahan (diperparah) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rendah | 76 | 8 (10,5 %) | 9 (11,8 %) | 59 (77,6 %) | 0 (0,0 %) | 19,85 menit | 18,29 menit | 11,99 menit |
| Sedang | 76 | 52 (68,4 %) | 7 (9,2 %) | 15 (19,7 %) | 2 (2,6 %) | 12,03 menit | 26,49 menit | 11,41 menit |
| Tinggi | 44 | 20 (45,5 %) | 3 (6,8 %) | 14 (31,8 %) | 7 (15,9 %) | 25,43 menit | 8,93 menit | 1,35 menit |

Dipicu = bukan TAS di Baseline, TES terdekat sama, waktu Baseline ke TES itu < 30 menit; diperparah = TAS di Baseline, TES sama, T_aktual naik > 1 menit; tidak berubah = TAS di Baseline, TES sama, perubahan ≤ 1 menit; lainnya = selain itu. Persentase terhadap TAS level tersebut.

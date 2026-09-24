# Diagnostik topologi jaringan jalan (branch `diagnostik-topologi`)

Ini diagnostik dan analisis sensitivitas saja. **Hasil terkunci v5 (`hasil-skripsi-v5`) tidak diubah**
dan jaringan utama tidak diganti. Definisi dan toleransi ditetapkan sebelum melihat hasil (commit
4642cef, `docs/CATATAN_TEMUAN.md`, bagian "Diagnostik topologi jaringan").

Hipotesis yang diuji: jalan memutar pada TAS adalah artefak topologi, karena segmen hanya tersambung
bila ujungnya identik setelah dibulatkan 0,01 m.

Reproduksi:

    python -m scripts.diagnostik_topologi       # langkah 1–4 (terdaftar)
    python -m scripts.eksplorasi_celah_lokal    # eksplorasi tambahan (tidak terdaftar, lihat §5)

Keluaran ada di `output_bab4/diagnostik_topologi/`. Pemeriksaan kewajaran lulus: graf yang dibangun
sama dengan `build_road_graph` di engine, dan perhitungan ulang pada graf asli mereproduksi status TAS
serta waktu minimum v5 secara persis di keempat level (`diagnostik_topologi.json`,
`reproduksi_v5_graf_mentah`).

## 1. Diagnostik topologi Baseline

| Ukuran | Nilai |
|---|---|
| Simpul | 156.751 |
| Panjang jaringan | 3.780,1 km |
| Jumlah komponen terhubung | 56 |
| Komponen terbesar: % simpul | 99,41 % |
| Komponen terbesar: % km | 99,53 % |
| Ujung buntu (derajat 1) | 4.703 |
| Near-miss ≤ 0,5 m | 0 |
| Near-miss ≤ 1 m | 2 |
| Near-miss ≤ 2 m | 4 |
| Near-miss ≤ 5 m | 17 |
| Perpotongan tanpa simpul bersama: total | 33 |
| … yang melibatkan jembatan/terowongan/layer ≠ 0 | 33 |
| … non-khusus (kandidat artefak) | **0** |

Catatan: angka near-miss dihitung per ujung buntu. Pasangan titik yang berdekatan (mis. 0,93 m ×2 dan
1,99 m ×2) adalah dua ujung buntu yang sama-sama dekat dengan sisi lain. Keterangan: segmen khusus =
1.263 segmen (jembatan, terowongan, atau layer ≠ 0).

Peta: `peta_near_miss_perpotongan.png`. Daftar: `near_miss.csv`, `perpotongan_tanpa_simpul.csv`.

Semua perpotongan tanpa simpul adalah persilangan bertingkat (jembatan/terowongan/layer), jadi memang
seharusnya tidak disambung. Near-miss sangat jarang: 4 dari 4.703 ujung buntu dalam radius 2 m.

## 2. Diagnostik per TAS (139 grid unik dari lembar validasi)

| Ukuran | Hasil |
|---|---|
| Simpul terdekat grid dan simpul terdekat TES berada di komponen yang sama | 139 dari 139 |
| Ada near-miss ≤ 2 m atau perpotongan non-khusus dalam 100 m dari garis grid–TES | 0 dari 139 |
| Klasifikasi "kemungkinan artefak topologi" | **0** |
| Klasifikasi "tidak terdeteksi artefak" | **139** |

Rincian per grid ada di `per_TAS.csv`.

## 3. Sensitivitas jaringan yang dirapikan

Perapian dilakukan dalam dua langkah: (a) noding perpotongan non-khusus, (b) menyambung near-miss
≤ toleransi. Toleransi utama 1 m, sensitivitas 2 m. Penutupan ruas per level tetap diterapkan, T_pen
v5 (403,87 menit) dipakai, dan tidak ada refit klaster.

| Jaringan | Komponen | Sambungan | Perpotongan disambung | Komponen terbesar % simpul / % km |
|---|---|---|---|---|
| v5 (asli) | 56 | – | – | 99,41 / 99,53 |
| dirapikan 1 m | 55 | 2 | 0 | 99,45 / 99,56 |
| dirapikan 2 m | 54 | 4 | 0 | 99,47 / 99,57 |

### Perbandingan v5 vs dirapikan

Hasil jaringan 1 m dan 2 m identik untuk semua ukuran di bawah. Sumber: `perbandingan_v5_vs_dirapikan.csv`.

| Ukuran | Baseline | Rendah | Sedang | Tinggi |
|---|---|---|---|---|
| TAS (aturan utama) v5 → dirapikan | 62 → 62 | 70 → 70 | 77 → 77 | 44 → 44 |
| TAS v5 yang hilang / TAS baru | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Terputus v5 → dirapikan | 111 → 110 | 126 → 125 | 502 → 501 | 651 → 650 |
| Jauh (20 menit) | 722 → 722 | 753 → 753 | 286 → 286 | 658 → 658 |
| Jauh (30 menit, utama) | 205 → 205 | 254 → 254 | 64 → 64 | 318 → 318 |
| Jauh (40 menit) | 33 → 33 | 29 → 29 | 4 → 4 | 171 → 171 |
| Median waktu minimum (menit) | 5,81 → 5,81 | 5,80 → 5,80 | 5,48 → 5,48 | 6,29 → 6,29 |
| P90 waktu minimum (menit) | 13,61 → 13,61 | 13,64 → 13,64 | 12,80 → 12,80 | 17,68 → 17,68 |
| P90 waktu minimum, hanya yang terjangkau | 13,329 → 13,330 | 13,304 → 13,305 | 11,724 → 11,726 | 14,583 → 14,584 |
| Baris Tipologi 4 (K = 4) v5 | 113 | 128 | 497 | 684 |
| … tak terjangkau jaringan di v5 | 111 | 126 | 493 | 639 |
| … menjadi terjangkau setelah dirapikan | 1 | 1 | 1 | 1 |

Catatan tentang dua baris:

- "Terputus" tidak bergantung pada ambang waktu, sehingga nilainya sama pada 20, 30, dan 40 menit.
- Pada "Tipologi 4 menjadi terjangkau", satu grid yang sama menjadi terjangkau di setiap level. Ini
  selaras dengan berkurangnya Terputus sebanyak 1.
- Perbandingan waktu memakai waktu tak-dibulatkan dari reproduksi graf asli, karena CSV terkunci
  membulatkan waktu ke 3 desimal (403,869 < T_pen 403,86917).

## 4. Peta sebelum/sesudah: 10 baris TAS v5 dengan DI tertinggi

Semua tetap berstatus TAS dengan T_aktual dan DI yang sama persis pada jaringan dirapikan 1 m. Peta ada di
`peta_sebelum_sesudah/`; tabel lengkap di `top10_DI_sebelum_sesudah.csv`.

| id_grid | Level | DI v5 | T_aktual v5 (mnt) | DI / T_aktual dirapikan | Status |
|---|---|---|---|---|---|
| 9017 | Tinggi | 118,5 | 357,1 | sama | TAS |
| 13219 | Tinggi | 116,2 | 72,9 | sama | TAS |
| 11859 | Tinggi | 101,1 | 358,0 | sama | TAS |
| 14598 | Baseline, Rendah, Sedang, Tinggi | 82,1 | 51,3 | sama | TAS |
| 13328 | Tinggi | 53,2 | 190,5 | sama | TAS |
| 8895 | Rendah, Sedang | 48,2 | 30,1 | sama | TAS |

## 5. Eksplorasi tambahan (TIDAK terdaftar sebelum melihat hasil)

Bagian ini bukan bagian dari uji hipotesis yang ditetapkan sebelumnya. Isinya hanya membantu menjelaskan
mengapa rute memutar. Script: `scripts/eksplorasi_celah_lokal.py`; keluaran: `celah_lokal_TAS.csv`.

Untuk tiap TAS unik, subgraf jaringan diambil dalam penyangga 200 m di sekitar garis grid–TES, lalu
diukur apakah sisi grid dan sisi TES terhubung di dalam penyangga itu. Jika tidak terhubung, diukur
jarak terpendek antara kedua bagian ("celah lokal").

- Terhubung di dalam penyangga: 18 dari 139. Rute memutar untuk grid ini terjadi karena jalan lokalnya
  memang panjang atau berkelok.
- Tidak terhubung: 121 dari 139. Dari jumlah itu, 118 memiliki celah terukur (3 sisanya: simpul terdekat
  berada di luar penyangga). Celah minimum 24,7 m, median 166,3 m, maksimum 540,2 m. Sebarannya: tidak ada
  yang < 20 m; 16 grid 20–50 m; 19 grid 50–100 m; 83 grid > 100 m.
- Jarak snapping grid ke simpul terdekat: median 50 m, maksimum 267 m. Jarak snapping TES: median 25 m,
  maksimum 259 m.

## 6. Penilaian

Hipotesis artefak topologi **tidak didukung**:

- Tidak ada perpotongan non-khusus tanpa simpul.
- Near-miss ≤ 2 m hanya 4 dan tidak ada yang berada di sekitar TAS mana pun.
- Jaringan dirapikan (1 m maupun 2 m) menghasilkan TAS yang identik di keempat level (0 hilang, 0 baru).
- Satu-satunya perubahan adalah 1 grid per level yang berpindah dari Terputus ke terjangkau. Perubahan ini
  tidak mengubah kategori Jauh, median, maupun P90.

Perbedaan ini **tidak cukup besar untuk mengganti jaringan utama**, sehingga tidak ada alasan menjalankan
v6. Menurut eksplorasi §5, rute memutar lebih mungkin mencerminkan salah satu dari tiga hal berikut:

1. Pemisahan nyata, seperti sungai, rel, lereng, atau sawah tanpa jalan. Celah lokal umumnya puluhan
   hingga ratusan meter, jauh di atas toleransi perapian.
2. Jalan/jembatan yang belum ada di OSM.
3. Pada level tinggi, penutupan ruas akibat genangan (mis. grid 9017, 11859, 13219, dan 13328 hanya
   TAS di level Tinggi).

Penyebab per grid sebaiknya dipastikan lewat lembar validasi (`output_bab4/validasi/validasi_TAS.xlsx`),
misalnya dengan mencatat kategori sungai / rel / lereng / data OSM / penutupan genangan. Jarak snapping
yang panjang pada sebagian grid juga layak disebut sebagai keterbatasan.

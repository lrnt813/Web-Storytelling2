# Diagnostik konsistensi kelas bahaya ruas jalan vs grid (Putaran 3, Langkah 1)

Model tidak diubah. Semua angka berasal dari data masukan dan aturan kode `hasil-skripsi-v2`.
Angka mentah ada di `output_bab4/diagnostik/diagnostik_jalan_grid.json` dan
`output_bab4/diagnostik/kontrafaktual_kelas_ruas.json`. Peta ada di
`output_bab4/diagnostik/ruas_tertutup_sedang.png` dan `ruas_tertutup_tinggi.png`.

## 1. Asal kelas bahaya (dari kode dan data)

| Objek | Berkas | Kolom | Unit | Cara kode memakainya |
|---|---|---|---|---|
| Grid | `data/Kulonprogo_Ready4.gpkg` | `banjir` (int 0–3) | poligon 100 × 100 m (22.673 grid, 225,9 km²) | Grid Tergenang ⇔ `banjir` ∈ kelas_ditutup (`simulate_hazard`) |
| Ruas jalan | `data/Kulonprogo_Jalan.gpkg` | `banjir` (int 0–3) | 162.608 segmen OSM (3.780 km, median 14 m) | Ruas ditutup ⇔ `banjir` ruas ∈ kelas_ditutup (`road_closed_mask`) |
| TES | `data/Kulonprogo_*.gpkg` (5 berkas) | `banjir` (int 0–3) | titik | TES valid ⇔ kelas < 2, ditambah aturan radius 50 m dari grid Tergenang |

- Ketiga kelas adalah **atribut siap pakai** di masing-masing GPKG. Tidak ada kode di repositori
  yang menurunkannya: tidak ada overlay, sampling raster, atau zonal statistics. Asal-usul dan
  metodenya berada di luar repositori.
- Segmen jalan terpotong per verteks OSM (median 14 m, dan 12,4% `osm_id` memiliki lebih dari satu
  kelas). Batas segmen **tidak sejajar** dengan grid raster manapun: pada kelipatan 100 m, 30 m,
  1″, 3″, dan 0,0001°–0,001° hanya ±4% ujung segmen jatuh di garis grid, setara peluang acak. Jadi
  kelas ruas tidak berasal dari overlay dengan grid 100 m penelitian ini.
- **Cakupan berbeda.** Grid hanya mencakup 225,9 km² (sel terpilih), sedangkan jaringan jalan
  mencakup seluruh kabupaten. Hanya 2.370 km dari 3.780 km jalan (63%) yang berada di dalam grid.

## 2. Kelas ruas vs kelas grid yang dilalui

Panjang jalan (km) di dalam grid, setelah ruas dipotong per grid:

| Kelas ruas \ kelas grid | 0 | 1 | 2 | 3 |
|---|---:|---:|---:|---:|
| 0 | 1.249,4 | 5,7 | 238,4 | 72,9 |
| 1 | 103,2 | 5,6 | 208,1 | 75,3 |
| 2 | 57,6 | 13,3 | 197,8 | 139,1 |
| 3 | 0,3 | 0,0 | 0,7 | 2,6 |

Kesesuaian (diagonal) hanya 1.455 km dari 2.370 km (61%). Tiga ketidaksesuaian menonjol:

- **Kelas 3.** Grid kelas 3 (2.531 grid) dilalui 290 km jalan, tetapi hanya 2,6 km berkelas ruas 3.
  Total ruas kelas 3 hanya 56 km di seluruh kabupaten, dan 94% di antaranya berada di luar grid.
- **Kelas 1.** Hanya 196 grid berkelas 1, tetapi ruas kelas 1 sepanjang 479 km. Di dalam grid, ruas
  kelas 1 sebagian besar melintasi grid kelas 2–3 (283 km) atau kelas 0 (103 km).
- **Kelas 2.** Ruas kelas 2 (646 km) sebagian melintasi grid kelas 0 (58 km).

## 3. Ruas yang ditutup per level

Ruas yang melintasi beberapa grid dipotong per grid (1 ruas rata-rata melintasi 1,25 grid).

| Level | Ruas ditutup | km ditutup | km di luar grid | km di grid Tergenang | km di grid non-Tergenang | Grid non-Tergenang dilalui ruas tertutup |
|---|---:|---:|---:|---:|---:|---:|
| Rendah (kelas 3) | 702 | 56,1 | 52,5 (94%) | 2,6 | 1,0 | 16 |
| Sedang (kelas ≥ 2) | 20.871 | 702,5 | 291,0 | 340,2 | 71,3 | 649 |
| Tinggi (kelas ≥ 1) | 41.619 | 1.181,5 | 377,7 | 642,6 | 161,1 | 1.433 |

km ruas tertutup di dalam grid, menurut kelas grid yang dilalui:

| Level | Grid kelas 0 | 1 | 2 | 3 |
|---|---:|---:|---:|---:|
| Rendah | 0,3 | 0,0 | 0,7 | 2,6 |
| Sedang | 57,9 | 13,3 | 198,5 | 141,7 |
| Tinggi | 161,1 | 19,0 | 406,6 | 217,0 |

Jalan **terbuka** di dalam grid Tergenang (km di grid Tergenang dikurangi km ruas tertutup di sana):
Rendah ± 287 km, Sedang ± 595 km, Tinggi ± 317 km.

**Jawaban atas pertanyaan latar belakang.** Dari Sedang ke Tinggi, ruas tertutup naik 20.871 →
41.619 karena ruas **kelas 1** (20.748 segmen, 479 km) ikut ditutup. Ruas kelas 1 ini tersebar di
area yang gridnya berkelas 0 dan 2–3, sedangkan grid kelas 1 hanya 196, sehingga grid Tergenang
hanya bertambah 196. Ruas tertutup yang melintasi grid kelas 0 (kering pada semua level) naik dari
57,9 km (Sedang) ke 161,1 km (Tinggi), dan melintasi 1.433 grid non-Tergenang. Jadi temuan "grid
kering tetapi terputus" pada Tinggi sebagian besar lahir dari **kelas ruas yang berasal dari sumber
berbeda dengan kelas grid**, bukan dari aturan yang sama yang diterapkan konsisten.

## 4. Besaran dampak (kontrafaktual diagnostik, model tidak diubah)

Kelas ruas diganti dengan kelas grid yang dilaluinya, lalu aksesibilitas dan TAS dihitung ulang.
T_pen dikunci sama (403,87 menit).

| Level | Varian | Ruas ditutup | Terputus | Terisolasi (non-Tergenang) | Rerata waktu min. (menit) | TAS |
|---|---|---:|---:|---:|---:|---:|
| Rendah | **data asli (v2)** | 702 | 162 | 109 | 9,84 | 1.652 |
| | A: maks. kelas grid; di luar grid tetap | 13.516 | 769 | 485 | 17,43 | 1.467 |
| | B: kelas grid mayoritas panjang; di luar grid tetap | 12.611 | 733 | 443 | 16,55 | 1.495 |
| | C: maks. kelas grid; di luar grid terbuka | 12.914 | 738 | 454 | 16,83 | 1.509 |
| Sedang | **data asli (v2)** | 20.871 | 819 | 703 | 27,10 | 1.042 |
| | A | 44.948 | 1.668 | 1.578 | 49,75 | 948 |
| | B | 43.772 | 1.597 | 1.522 | 48,27 | 953 |
| | C | 39.861 | 1.298 | 1.162 | 39,96 | 943 |
| Tinggi | **data asli (v2)** | 41.619 | 1.576 | 1.320 | 43,77 | 958 |
| | A | 48.906 | 1.618 | 1.510 | 48,48 | 942 |
| | B | 47.800 | 1.562 | 1.470 | 47,40 | 940 |
| | C | 40.699 | 1.184 | 1.071 | 37,87 | 935 |

Median waktu minimum hampir tidak berubah (6–7 menit). Dampak utamanya ada pada ekor distribusi:
jumlah grid Terputus/terisolasi dan rerata waktu. Dampak terbesar terjadi di **Level Rendah**. Dengan
data asli, Rendah praktis tidak menutup jalan di area penelitian (hanya 3,6 km di dalam grid), padahal
2.531 grid tergenang. Dengan kelas yang diselaraskan, Terputus naik ±4,5× dan rerata waktu ±1,7×.
Urutan level juga berubah: dengan varian A, Sedang lebih buruk daripada Tinggi pada rerata waktu,
karena pada data asli Tinggi terbantu oleh ruas di luar grid yang tetap terbuka.

Kelas **TES** juga tidak selaras dengan grid: 196 TES berkelas 0 berada di grid kelas 2–3, 253 TES
berkelas 1 berada di grid kelas 2–3, dan 212 TES berada di luar area grid. Sebagian ketidaksesuaian
ini sudah dikoreksi oleh aturan radius 50 m dari grid Tergenang.

## 5. Kesimpulan

Penyebabnya adalah **perbedaan sumber data**: kelas bahaya ruas jalan (dan TES) adalah atribut
tersendiri di GPKG masing-masing, dengan unit, segmentasi, dan cakupan yang berbeda dari kelas grid.
Hasilnya tidak konsisten dengan aturan "kelas yang sama ditutup". Sesuai instruksi, **tidak ada yang
diperbaiki**. Keputusan ada di peneliti dan pembimbing.

## 6. Opsi solusi

1. **Selaraskan penutupan ruas ke kelas grid** (varian A atau B di atas; opsional juga TES → kelas grid).
   Ruas ditutup bila melintasi grid Tergenang (A: kelas grid maksimum; B: kelas grid mayoritas
   panjang). Untuk ruas di luar area grid, ada dua pilihan: tetap memakai atribut sendiri, atau
   dianggap terbuka (C).
   - Konsekuensi: aturan "kelas yang sama ditutup" berlaku konsisten di area penelitian. Angka Rendah
     dan Sedang berubah besar (Terputus 4,5× dan 2× lipat). Seluruh analisis v3 dijalankan dengan
     jaringan baru. Ruas di luar grid tetap memerlukan keputusan terpisah.
2. **Pertahankan data apa adanya dan laporkan sebagai keterbatasan.**
   - Konsekuensi: tidak ada perubahan angka v2. Namun level harus dijelaskan sebagai "kelas grid
     tergenang dan kelas ruas yang ditutup menurut atribut masing-masing", dan temuan "grid kering
     tetapi terputus" (terutama Tinggi) serta dampak ringan Level Rendah harus diberi catatan bahwa
     sebagian adalah artefak sumber data.
3. **Turunkan ulang kelas grid, ruas, dan TES dari satu sumber raster InaRisk** dengan metode yang sama
   (misalnya nilai raster maksimum atau mayoritas per potongan ruas per grid, dan per titik TES).
   - Konsekuensi: paling konsisten dan paling mudah dipertahankan saat sidang. Namun raster sumber
     tidak ada di repositori dan harus disediakan. Semua angka berubah, dan metode penurunan kelas
     harus didokumentasikan.

## 7. Pembaruan setelah raster sumber tersedia (keputusan: opsi 3)

Pengguna menyediakan `data/Kulonprogo_Banjir.tif`: raster InaRisk, EPSG:32749, resolusi 29,71 m,
1.002 × 1.278 piksel, nilai 1 = rendah, 2 = sedang, 3 = tinggi, nodata 15. Hasil uji asal-usul:

| Objek | Metode uji | Kecocokan dengan atribut lama |
|---|---|---:|
| TES | nilai piksel di titik | **100%** (1.647 / 1.647) |
| Ruas jalan | nilai piksel di titik tengah segmen | **98,7%** |
| Grid | mayoritas / maksimum / piksel centroid | **64–65%** |

**Koreksi kesimpulan §5.** Kelas ruas dan TES memang berasal dari raster ini. Yang berasal dari sumber
atau metode lain adalah **kelas grid**. Distribusi grid lama [0: 14.632; 1: 196; 2: 5.314; 3: 2.531]
tidak dapat direproduksi dari raster dengan metode apa pun. Contohnya, raster hanya memuat 8,7 km²
kelas 3, sedangkan grid lama kelas 3 berjumlah 25,3 km².

**Keputusan peneliti.** Semua kelas diturunkan dari raster dengan metode berikut:

- grid: kelas mayoritas piksel yang pusatnya di dalam grid (kelas 0 ikut dihitung), seri → kelas
  terendah, grid tanpa pusat piksel → piksel di centroid;
- ruas: kelas maksimum piksel sepanjang segmen (sampel tiap ≤ 5 m);
- TES: piksel di titik.

Nilai nodata dianggap kelas 0. Implementasi ada di `backend/hazard_raster.py`, diterapkan saat data
dimuat (`load_data`, `load_road_network`). Atribut lama disimpan sebagai `banjir_atribut_lama`.

Hasil turunan raster:

- grid [0: 15.498; 1: 3.800; 2: 3.336; 3: 39], sehingga grid Tergenang Rendah 39, Sedang 3.375,
  Tinggi 7.175 (lama: 2.531 / 7.845 / 8.041);
- ruas [0: 118.512; 1: 23.133; 2: 20.253; 3: 710] (98,5% sama dengan atribut lama, 2.477 ruas naik
  kelas karena aturan maksimum);
- TES identik dengan atribut lama.

Dengan grid mayoritas dan ruas maksimum, ruas tertutup masih dapat melintasi grid yang mayoritasnya
kering. Konsekuensi ini sudah diterima peneliti saat memilih metode.

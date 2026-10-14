# Dataset

Semua data ada di folder `data/`. Data spasial memakai CRS **EPSG:32749** (WGS 84 / UTM zona 49S), kecuali
batas administrasi (EPSG:4326). Berkas GeoPackage (`*.gpkg`) disimpan dengan **Git LFS**; jalankan
`git lfs pull` setelah clone bila berkas masih berupa pointer teks kecil.

## 1. Data masukan

| Berkas | Isi | Jumlah fitur | Geometri |
|---|---|---|---|
| `Kulonprogo_Ready4.gpkg` | Grid analisis 100 × 100 m Kabupaten Kulon Progo | 22.673 | MultiPolygon |
| `Kulonprogo_Jalan.gpkg` (layer `Kulonprogo_Jalan2`) | Jaringan jalan OpenStreetMap | 162.608 segmen | LineString |
| `Kulonprogo_Pendidikan.gpkg` | Bangunan pendidikan (kandidat TES) | 548 | Point |
| `Kulonprogo_Faskes.gpkg` | Fasilitas kesehatan (kandidat TES) | 29 | Point |
| `Kulonprogo_Kantor.gpkg` | Kantor pemerintahan (kandidat TES) | 238 | Point |
| `Kulonprogo_Ibadah.gpkg` | Tempat ibadah (kandidat TES) | 791 | Point |
| `Kulonprogo_GOR.gpkg` | GOR/gedung serbaguna (kandidat TES) | 41 | Point |
| `Kulonprogo_Banjir.tif` | Raster indeks bahaya banjir InaRisk (piksel 29,71 m; 0 = nodata/aman, 1 = rendah, 2 = sedang, 3 = tinggi) | 1278 × 1002 piksel | Raster uint8 |
| `KulonProgo_Desa.gpkg` | Batas desa/kalurahan (BIG 1:10.000) + kolom penduduk | 88 | MultiPolygon Z |
| `KulonProgo_Kec.gpkg` | Batas kecamatan/kapanewon (BIG 1:10.000) | 12 | MultiPolygon Z |
| `Penduduk_Desa_KulonProgo.csv` | Jumlah penduduk per kalurahan (kolom `Kalurahan/Village`, `Penduduk`) | 88 baris | – |

Kolom yang dipakai analisis:

- **Grid (`Kulonprogo_Ready4.gpkg`):** `Id` (ID grid asli), `Road_Density_mean` (kerapatan jaringan jalan),
  dan geometri. Atribut `banjir` bawaan diganti oleh kelas bahaya turunan raster saat data dimuat (disimpan
  sebagai `banjir_atribut_lama`). Kolom lain di berkas ini (mis. `cl_sdwfcm_*`, `PSI_*`, `curah_hujan`)
  berasal dari tahap penelitian sebelumnya dan tidak dipakai analisis final.
- **Jalan:** geometri segmen, `fclass`, `oneway`; kelas bahaya ruas diturunkan dari raster.
- **TES:** `nama`, `Kategori`, koordinat; kelas bahaya TES diturunkan dari raster pada titik TES.
- **Desa:** `NAMOBJ` (nama kalurahan), `WADMKC` (kapanewon), serta kolom tambahan `penduduk`, `luas_km2`,
  `kepadatan_jiwa_km2` (dibuat oleh `python -m scripts.penduduk_desa`).

## 2. Hasil pemodelan

| Berkas | Isi |
|---|---|
| `thesis_results.json` | Ringkasan seluruh hasil: data, level, pra-pemrosesan, pemilihan K, model per K, transisi, validitas, waktu komputasi |
| `thesis_grid_results.csv.gz` | Satu baris per grid (22.673 baris, 127 kolom): waktu tempuh per kategori TES dan level, status Tergenang, TAS, kategori akses, atribusi banjir, klaster dan keanggotaan per level dan K |
| `thesis_pooled_results.csv.gz` | Data gabungan: satu baris per pasangan (grid, level) non-Tergenang, berisi fitur, komponen utama, label klaster, dan derajat keanggotaan per K |
| `locked/` | Salinan terkunci ketiga berkas di atas beserta `LOCK.json` (checksum dan versi pustaka). Dashboard dan `export_bab4` membaca dari sini |
| `locked/arsip_*` | Hasil versi sebelumnya (v1–v5) untuk keterlacakan revisi |

Pola nama kolom penting di `thesis_grid_results.csv.gz` (`{level}` = `baseline`, `rendah`, `sedang`, `tinggi`;
`{k}` = 2, 3, 4):

| Kolom | Arti |
|---|---|
| `id_grid`, `id_grid_asli` | Nomor urut grid (kunci join dashboard) dan ID grid asli |
| `tergenang_{level}` | 1 bila grid tergenang pada level tersebut |
| `waktu_{kategori}_{level}`, `waktu_min_{level}` | Waktu tempuh berjalan kaki (menit) ke TES terdekat per kategori dan minimumnya |
| `t_ideal_{level}`, `t_aktual_{level}`, `di_{level}` | Waktu ke TES terdekat secara garis lurus (ideal) dan lewat jaringan jalan (aktual), serta Detour Index = aktual/ideal |
| `tas_{level}`, `tas_status_{level}` | Titik Aman Semu dan statusnya |
| `akses_{level}` | Kategori akses (batas 30 menit) |
| `atribusi_banjir_{level}`, `tambahan_waktu_{level}` | Pengaruh banjir pada TAS dan tambahan waktu terhadap Baseline |
| `cl_{level}_k{k}`, `mem_{level}_k{k}` | Nomor tipologi SDWFCM dan derajat keanggotaan maksimum |

## 3. Data turunan untuk dashboard

- `frontend/static_grid_kulonprogo.geojson`: geometri grid ringan (dibuat oleh `python -m scripts.export_geometry`).
- `scratch/graph_cache/`: cache graf jalan yang dibuat otomatis saat server pertama kali berjalan (tidak disimpan di repositori).

## 4. Sumber dan lisensi

- Batas administrasi: Badan Informasi Geospasial (BIG), skala 1:10.000.
- Jaringan jalan: © OpenStreetMap contributors (ODbL).
- Indeks bahaya banjir: InaRisk, BNPB.
- Data penduduk per kalurahan: **[lengkapi sumber dan tahun]**.
- Titik bangunan publik (TES): **[lengkapi sumber dan tahun]**.

# Dokumentasi Sistem

Dokumen ini menjelaskan arsitektur, modul, alur data, dan antarmuka (API) dashboard serta pipeline
pemodelan. Metode dan persamaan lengkap ada di `docs/METODOLOGI.md`; kamus data di `docs/DATASET.md`;
cara memakai dashboard di `docs/PANDUAN_PENGGUNAAN.md`.

## 1. Gambaran umum

Sistem terdiri atas dua bagian yang memakai kode komputasi yang sama (`backend/engine.py`,
`backend/thesis.py`):

1. **Pipeline pemodelan (offline).** `scripts/thesis_analysis.py` membaca data spasial di `data/`,
   menghitung waktu tempuh grid → TES pada empat level banjir, menjalankan SDWFCM pada data gabungan,
   memilih K berbasis stabilitas, lalu menulis hasil ke `data/thesis_results.json`,
   `data/thesis_grid_results.csv.gz`, dan `data/thesis_pooled_results.csv.gz`. Hasil final dikunci di
   `data/locked/` (checksum di `LOCK.json`). `scripts/export_bab4.py` mengubah hasil terkunci menjadi
   tabel, peta, dan dokumen Bab IV di `output_bab4/`.
2. **Dashboard (online, lokal).** Server FastAPI (`backend/main.py`) memuat hasil terkunci dan data
   spasial, lalu menyajikannya ke frontend Leaflet (`frontend/`). Untuk simulasi blokir jalan dan rute
   evakuasi, server menghitung ulang pada graf jalan di memori. Simulasi tidak mengubah hasil penelitian.

```text
 data/*.gpkg, *.tif ──► scripts/thesis_analysis.py ──► data/thesis_*  ──► data/locked/ (kunci)
                          (backend/thesis.py,                                │
                           backend/engine.py)                                ├──► scripts/export_bab4.py ──► output_bab4/
                                                                             │
                                                                             └──► backend/main.py (FastAPI) ◄──► frontend/ (Leaflet)
```

## 2. Teknologi

| Lapisan | Teknologi |
|---|---|
| Bahasa | Python 3.14.7 (`.python-version`), JavaScript (ES2020) |
| Server | FastAPI, Uvicorn, Pydantic |
| Analisis spasial | GeoPandas, Shapely, PyProj, Pyogrio, Rasterio, NetworkX, libpysal, esda |
| Pemodelan | NumPy, SciPy, scikit-learn, spopt (REDCAP/SKATER pembanding), numba |
| Frontend | HTML, CSS, JavaScript tanpa build step; Leaflet 1.9.4 (peta), SheetJS (unduh Excel), Font Awesome (ikon) |
| Uji | pytest, httpx |
| Pelaporan | python-docx, openpyxl, Matplotlib |

Versi pustaka dipin persis di `requirements.txt` agar hasil dapat direproduksi.

## 3. Struktur berkas

```text
backend/
  main.py           Aplikasi FastAPI: endpoint API, pemuatan data saat start, cache graf jalan
  thesis.py         Metodologi Bab III–IV: level banjir, data gabungan, pra-pemrosesan, SDWFCM,
                    pemilihan K, penomoran klaster, transisi, Titik Aman Semu (TAS), atribusi banjir
  engine.py         Komputasi dasar: pemuatan data, graf jalan, snapping ruas, waktu tempuh (Dijkstra),
                    algoritma klaster (SDWFCM, FCM, SFCM, REDCAP, SKATER)
  sdwfcm_guo.py     SDWFCM versi asli Guo dkk. (2015) sebagai pembanding
  desc_n.py         Indeks DESC-N dan PESC-N (DESC/PESC ternormalisasi)
  hazard_raster.py  Turunan kelas bahaya grid/ruas/TES dari raster InaRisk
  road_cut.py       Indeks spasial ruas jalan untuk menempelkan titik blokir ke ruas terdekat
  config.py         Level banjir, label tipologi, pengaturan K utama
  state.py          Status data di memori server
  schemas.py        Skema permintaan API (Pydantic)
frontend/
  index.html        Halaman dashboard
  css/styles.css    Tampilan
  js/config.js      Konstanta, warna, level, fungsi bantu
  js/map-layers.js  Peta dasar, grid, TES, jalan, pergantian level/tampilan, blokir jalan, pembanding level
  js/routing.js     Popup detail grid dan rute evakuasi
  js/legend.js      Legenda per tampilan
  js/boundaries.js  Batas kabupaten/kapanewon/kalurahan
  js/regions.js     Ringkasan dan peringkat prioritas wilayah
  js/search.js      Pencarian wilayah dan alamat
  js/results.js     Panel "Hasil Penelitian" (tabel dan grafik Bab IV)
  js/export.js      Unduh tabel (Excel/CSV) dan grafik (PNG)
  js/bootstrap.js   Inisialisasi halaman
  static_grid_kulonprogo.geojson  Geometri grid (dibuat oleh scripts/export_geometry.py)
scripts/
  thesis_analysis.py         Menjalankan seluruh pipeline pemodelan
  kunci_hasil.py             Mengunci hasil ke data/locked/ (checksum)
  cek_reproduksi.py          Menjalankan ulang ke folder sementara dan membandingkan hash
  export_bab4.py             Membangun output_bab4/ (tabel CSV, Tabel_Bab4.docx, peta, ringkasan)
  keputusan_k_v6.py          Membuat docs/KEPUTUSAN_K_v6.md
  reproduksi_label_v6.py     Reproduksi label K 5–10 dan algoritma pembanding
  metrik_finalisasi_v6.py    Metrik DESC-N/PESC-N dan perbandingan dengan SDWFCM Guo
  validasi_desc_n_sintetis.py  Validasi DESC-N/PESC-N pada data buatan
  lembar_validasi_TAS.py     Membuat lembar validasi manual TAS (Excel)
  rekap_validasi_TAS.py      Merekap hasil validasi manual TAS
  dampak_koreksi_snapping.py Dampak koreksi snapping ruas (v5 → v6)
  penduduk_desa.py           Menambahkan kolom penduduk ke batas desa dan membuat peta sebaran penduduk
  peta_util.py               Kelengkapan peta: batas Kabupaten Kulon Progo, arah utara, skala batang (EPSG:32749)
  export_geometry.py         Ekspor geometri grid untuk frontend
tests/              Uji unit dan uji API (pytest)
data/               Dataset dan hasil pemodelan (lihat docs/DATASET.md)
output_bab4/        Keluaran Bab IV (tabel, peta, dokumen)
docs/               Dokumentasi
start_dashboard.py  Peluncur dashboard (lokal; --publik untuk alamat sementara Cloudflare Tunnel)
main.py             Titik masuk kompatibilitas (`uvicorn main:app`)
pengaturan_hasil.json  K utama dan deskripsi tipologi untuk tabel dan dashboard
```

## 4. Alur pemodelan

1. **Level banjir.** Empat level ditentukan oleh kelas bahaya InaRisk yang ditutup: Baseline (tidak ada),
   Rendah (kelas 3), Sedang (kelas ≥ 2), Tinggi (kelas ≥ 1). Grid dan ruas jalan pada kelas yang ditutup
   tidak dapat dilalui; grid tersebut berstatus *Tergenang* dan berada di luar klasterisasi.
2. **Waktu tempuh.** Dari centroid setiap grid ke TES terdekat per kategori (pendidikan, kesehatan,
   pemerintahan, ibadah, GOR) melalui jaringan jalan dengan snapping ke ruas terdekat; kecepatan berjalan
   kaki 80 m/menit.
3. **Data gabungan dan pra-pemrosesan.** Semua pasangan (grid, level) non-Tergenang digabung; transformasi
   di-fit sekali pada data gabungan.
4. **SDWFCM.** Matriks bobot spasial KNN-Gaussian blok-diagonal per level. K dipilih berbasis stabilitas
   subsampel (ARI); model utama K = 4, dengan K = 2 dan K = 3 sebagai sensitivitas.
5. **Penomoran dan label.** Klaster diurutkan menurut rata-rata waktu tempuh minimum (Tipologi 1 = akses
   paling dekat), dan diberi deskripsi kombinasi akses dan jaringan jalan (`pengaturan_hasil.json`).
6. **Analisis lanjutan.** Transisi tipologi antarlevel, perbandingan algoritma (FCM, SFCM, REDCAP, SKATER,
   SDWFCM Guo), Titik Aman Semu (Detour Index), kategori akses (batas 30 menit), atribusi pengaruh banjir.
7. **Penguncian dan pelaporan.** Hasil dikunci (`kunci_hasil.py`), lalu `export_bab4.py` membangun tabel
   dan peta Bab IV.

## 5. API dashboard

Dokumentasi interaktif tersedia di `http://127.0.0.1:8000/docs` saat server berjalan.

| Metode | Endpoint | Fungsi |
|---|---|---|
| GET | `/api/health` | Status server dan data |
| GET | `/api/levels` | Daftar level banjir |
| GET | `/api/baseline?level=&k=` | Tipologi SDWFCM per grid untuk satu level dan K |
| GET | `/api/thesis-results` | Ringkasan seluruh hasil Bab IV (untuk panel Hasil Penelitian) |
| POST | `/api/simulate` | Simulasi blokir jalan: hitung ulang waktu tempuh dan keanggotaan klaster |
| GET | `/api/snap-road?lat=&lng=` | Tempelkan titik klik ke ruas jalan terdekat (ditolak bila bukan jalan) |
| POST | `/api/route-all-tes` | Rute evakuasi dari grid/titik ke TES terdekat setiap kategori |
| POST | `/api/roads` | Jaringan jalan dengan status ruas terputus per level |
| GET | `/api/tes-layers?level=` | Titik TES per kategori dan status aktifnya |
| GET | `/api/admin-boundaries` | Batas kabupaten, kapanewon, dan kalurahan |
| GET | `/api/grid-admin` | Kalurahan dan kapanewon setiap grid |
| GET | `/api/search-list` | Daftar wilayah untuk pencarian |
| GET | `/api/geocode?q=` | Pencarian alamat (OpenStreetMap Photon dan Nominatim; perlu internet) |

## 6. Simulasi blokir jalan

Titik klik pengguna ditempelkan ke ruas jalan terdekat (toleransi bawaan 25 m, maksimum 75 m);
klik di luar jaringan jalan ditolak. Hanya ruas yang diklik yang diputus. Server menghitung ulang
waktu tempuh level terpilih, lalu menghitung keanggotaan terhadap **pusat klaster final yang tetap**
(model tidak di-fit ulang), sehingga nomor tipologi tetap bermakna sama. Hasil simulasi ditandai
"Mode Simulasi" dan bukan hasil skripsi (METODOLOGI §14).

## 7. Pengujian

```bash
python -m pytest -q              # uji unit
SMOKE_API=1 python -m pytest -q tests/test_api_smoke.py   # uji API dashboard (bash)
# PowerShell: $env:SMOKE_API="1"; python -m pytest -q tests/test_api_smoke.py
```

Uji mencakup pra-pemrosesan, SDWFCM, penomoran klaster, TAS, snapping ruas, atribusi banjir, ekspor
tabel, blokir jalan, dan endpoint API.

## 8. Reproduksibilitas

Seed tetap dan satu thread BLAS/OpenMP. `python -m scripts.cek_reproduksi` menjalankan ulang pipeline ke
folder sementara dan membandingkan hash dengan hasil terkunci (lihat README). Aturan perubahan metode
dan penguncian hasil: `docs/ALUR_KERJA.md`.

# Aksesibilitas TES Banjir · Kulon Progo

Dashboard informasi dan kode pemodelan skripsi: pemetaan tingkat aksesibilitas spasial bangunan publik sebagai
Tempat Evakuasi Sementara (TES) banjir di Kabupaten Kulon Progo dengan *Spatial Distance-Weighted Fuzzy
C-Means* (SDWFCM) pada grid 100 × 100 m.

## Identitas

| | |
|---|---|
| Judul | **[judul skripsi resmi]** |
| Nama | **[nama lengkap]** |
| NIM | **[NIM]** |
| Program Studi | **[program studi]** |
| Fakultas / Universitas | **[fakultas, universitas]** |
| Dosen Pembimbing | **[nama dosen pembimbing]** |
| Tahun | **[tahun]** |
| Jenis artifak | Information Dashboard (aplikasi web) |

## Deskripsi

Wilayah Kulon Progo dibagi menjadi 22.673 grid 100 × 100 m. Untuk setiap grid dihitung waktu tempuh berjalan
kaki ke TES terdekat (pendidikan, kesehatan, pemerintahan, ibadah, GOR) melalui jaringan jalan pada empat level
banjir (Baseline, Rendah, Sedang, Tinggi; berdasarkan kelas bahaya InaRisk). Grid non-tergenang dikelompokkan
dengan SDWFCM menjadi empat tipologi aksesibilitas (kombinasi kedekatan akses dan kerapatan jaringan jalan).
Analisis dilengkapi transisi tipologi antarlevel, perbandingan algoritma, Titik Aman Semu (Detour Index),
kategori akses, dan atribusi pengaruh banjir.

Dashboard menampilkan peta tipologi, grid tergenang, TAS, dan waktu tempuh per level; detail dan rute evakuasi
tiap grid; perbandingan antarlevel; prioritas wilayah per kalurahan/kapanewon; pencarian alamat; tabel dan
grafik Bab IV yang dapat diunduh; serta **simulasi blokir jalan** yang menghitung ulang aksesibilitas dan
tipologi secara langsung.

## Mulai cepat

```bash
git lfs install
git clone <URL-REPOSITORI> && cd <nama-folder>
pip install -r requirements.txt     # Python 3.14
python start_dashboard.py           # buka http://127.0.0.1:8000
```

Langkah lengkap, cara memakai setiap fitur, dan pemecahan masalah: **[docs/PANDUAN_PENGGUNAAN.md](docs/PANDUAN_PENGGUNAAN.md)**.

## Dokumentasi

| Dokumen | Isi |
|---|---|
| [docs/PANDUAN_PENGGUNAAN.md](docs/PANDUAN_PENGGUNAAN.md) | Instalasi, menjalankan dashboard, memakai fitur, menjalankan ulang pemodelan |
| [docs/DOKUMENTASI_SISTEM.md](docs/DOKUMENTASI_SISTEM.md) | Arsitektur, modul, alur pemodelan, API, pengujian |
| [docs/DATASET.md](docs/DATASET.md) | Kamus data masukan dan hasil pemodelan, sumber data |
| [docs/METODOLOGI.md](docs/METODOLOGI.md) | Metode dan persamaan sebagaimana diimplementasikan |
| [docs/RUJUKAN_PARAMETER.md](docs/RUJUKAN_PARAMETER.md) | Rujukan nilai parameter |
| [docs/KEPUTUSAN_K_v6.md](docs/KEPUTUSAN_K_v6.md) | Dasar pemilihan jumlah klaster (K = 4) |
| [docs/ALUR_KERJA.md](docs/ALUR_KERJA.md) | Aturan perubahan metode dan penguncian hasil |
| [docs/CATATAN_TEMUAN.md](docs/CATATAN_TEMUAN.md) | Catatan temuan dan keputusan selama revisi |
| [docs/DIAGNOSTIK_JALAN_GRID.md](docs/DIAGNOSTIK_JALAN_GRID.md), [docs/DAMPAK_KOREKSI_SNAPPING.md](docs/DAMPAK_KOREKSI_SNAPPING.md) | Diagnostik data dan dampak koreksi |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Membagikan dashboard sementara lewat Cloudflare Tunnel |

## Struktur berkas

```text
.
├── README.md                    Identitas, deskripsi, dan struktur repositori
├── requirements.txt             Pustaka Python (versi dipin)
├── .python-version              Versi Python (3.14.7)
├── pengaturan_hasil.json        K utama dan deskripsi tipologi
├── start_dashboard.py           Peluncur dashboard (--publik untuk alamat sementara)
├── main.py                      Titik masuk kompatibilitas (uvicorn main:app)
├── Jalankan Dashboard.bat       Peluncur klik-dua-kali (Windows)
├── Jalankan Dashboard Publik.bat
├── Dockerfile, .dockerignore    Image container (opsional)
│
├── backend/                     KODE ARTIFAK (server) DAN KODE PEMODELAN
│   ├── main.py                  Aplikasi FastAPI (API dashboard)
│   ├── thesis.py                Pipeline metodologi: level banjir, SDWFCM, pemilihan K, transisi, TAS
│   ├── engine.py                Data, graf jalan, waktu tempuh, algoritma klaster
│   ├── sdwfcm_guo.py            SDWFCM versi asli Guo dkk. (2015) sebagai pembanding
│   ├── desc_n.py                Indeks DESC-N / PESC-N
│   ├── hazard_raster.py         Kelas bahaya dari raster InaRisk
│   ├── road_cut.py              Penempelan titik blokir ke ruas jalan
│   └── config.py, state.py, schemas.py
│
├── frontend/                    KODE ARTIFAK (antarmuka web)
│   ├── index.html
│   ├── css/styles.css
│   ├── js/                      Peta, rute, legenda, pencarian, wilayah, hasil penelitian, unduhan
│   └── static_grid_kulonprogo.geojson
│
├── scripts/                     KODE PEMODELAN DAN PELAPORAN
│   ├── thesis_analysis.py       Menjalankan seluruh pemodelan
│   ├── kunci_hasil.py           Mengunci hasil (checksum)
│   ├── cek_reproduksi.py        Uji reproduksi hasil
│   ├── export_bab4.py           Tabel, peta, dan dokumen Bab IV
│   ├── keputusan_k_v6.py, reproduksi_label_v6.py, metrik_finalisasi_v6.py, validasi_desc_n_sintetis.py
│   ├── lembar_validasi_TAS.py, rekap_validasi_TAS.py, dampak_koreksi_snapping.py
│   ├── penduduk_desa.py         Kolom penduduk dan peta sebaran penduduk per desa
│   ├── peta_util.py             Batas kabupaten, arah utara, dan skala pada peta
│   └── export_geometry.py       Geometri grid untuk frontend
│
├── data/                        DATASET (lihat docs/DATASET.md)
│   ├── Kulonprogo_Ready4.gpkg   Grid analisis 100 × 100 m
│   ├── Kulonprogo_Jalan.gpkg    Jaringan jalan
│   ├── Kulonprogo_{Pendidikan,Faskes,Kantor,Ibadah,GOR}.gpkg   Kandidat TES
│   ├── Kulonprogo_Banjir.tif    Indeks bahaya banjir InaRisk
│   ├── KulonProgo_Desa.gpkg, KulonProgo_Kec.gpkg   Batas administrasi
│   ├── Penduduk_Desa_KulonProgo.csv
│   ├── thesis_results.json, thesis_grid_results.csv.gz, thesis_pooled_results.csv.gz   Hasil pemodelan
│   └── locked/                  Hasil terkunci + LOCK.json; arsip_v1–v5 (versi sebelumnya)
│
├── output_bab4/                 HASIL: tabel CSV (T*, S*, L*), Tabel_Bab4.docx, peta, ringkasan angka
├── docs/                        DOKUMENTASI SISTEM DAN PANDUAN PENGGUNAAN
└── tests/                       Uji unit dan uji API (pytest)
```

## Reproduksi hasil

```bash
python -m pytest -q                  # uji unit
python -m scripts.cek_reproduksi     # jalankan ulang ke folder sementara dan bandingkan hash (± 2 jam; termasuk pemilihan K)
python -m scripts.export_bab4        # bangun ulang output_bab4/ dari data/locked/
```

Hasil final (`hasil-skripsi-v6`, K utama = 4) dikunci di `data/locked/`. Hash yang diharapkan:

| Besaran | SHA-256 |
|---|---|
| Fingerprint `thesis_results.json` tanpa field waktu dan `meta.git` | `e58b6e7e7814fc8d8e08f90ae64495da4f3259aeae1e4837c8de0995e9481a00` |
| Isi `thesis_grid_results.csv` (setelah dekompresi) | `9e9dc36860e7d57c873e9fee2f0b46e59bea623601342cadae1da974544f4de0` |
| Isi `thesis_pooled_results.csv` (setelah dekompresi) | `d4ea0ec5eba98ff9748fd6466a7de9e71a4e61354f7d868e60db0253a981c6f9` |

Semua angka skripsi diambil dari `output_bab4/`. Menjalankan ulang analisis dan mengunci hasil baru mengikuti
`docs/ALUR_KERJA.md`.

## Sumber data

Batas administrasi desa/kelurahan dan kecamatan: Badan Informasi Geospasial (skala 1:10.000). Jaringan jalan:
© OpenStreetMap contributors. Indeks bahaya banjir: InaRisk (BNPB). Rincian di `docs/DATASET.md`. Peta dasar
© Esri & OpenStreetMap contributors; pencarian alamat © OpenStreetMap contributors (Photon, Nominatim).

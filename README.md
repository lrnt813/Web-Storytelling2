# Aksesibilitas TES Banjir · Kulon Progo

Dashboard penelitian skripsi: pemetaan tingkat aksesibilitas spasial bangunan publik sebagai
Tempat Evakuasi Sementara (TES) banjir di Kabupaten Kulon Progo menggunakan
*Spatial Distance-Weighted Fuzzy C-Means* (SDWFCM) pada grid mikro 100 × 100 m.

**Fitur:** tipologi klaster per level intensitas banjir (Baseline, Rendah, Sedang, Tinggi),
Titik Aman Semu, rute evakuasi ke TES terdekat, simulasi blokir jalan, prioritas wilayah
per kalurahan/kapanewon, pembanding level, pencarian alamat, batas wilayah, serta tabel
dan grafik Bab IV yang dapat diunduh.

## Menjalankan di komputer sendiri

```bash
pip install -r requirements.txt
python start_dashboard.py            # lokal: http://127.0.0.1:8000
python start_dashboard.py --publik   # + alamat publik https://….trycloudflare.com
```

Di Windows cukup klik dua kali `Jalankan Dashboard.bat` atau `Jalankan Dashboard Publik.bat`.

Hasil analisis sudah tersedia dan dikunci di `data/locked/` (lihat bagian berikut).

## Reproduksi Hasil Skripsi

Lingkungan: Python 3.14.7 (`.python-version`) dan pustaka dengan versi persis di
`requirements.txt`. Versi yang dipakai saat penguncian juga tercatat di `data/locked/LOCK.json`.

```bash
pip install -r requirements.txt
python -m pytest -q                        # uji unit (±1 menit; SMOKE_API=1 untuk uji API dashboard)
python -m scripts.cek_reproduksi           # jalankan ulang ke folder sementara + bandingkan hash (±2,1 jam)
python -m scripts.export_bab4              # bangun ulang output_bab4/ dari data/locked/ (beberapa detik)
```

Hash yang diharapkan (hasil `hasil-skripsi-v3`: kelas bahaya dari raster InaRisk, keluaran K = 2 dan K = 3):

| Besaran | SHA-256 |
|---|---|
| Fingerprint `thesis_results.json` tanpa field waktu dan `meta.git` | `85bd479d9a4b899fe08340dd75e9df97ad085aadbcdb6e193eebdd75aefa4f0b` |
| Isi `thesis_grid_results.csv` (setelah dekompresi) | `8e139bace3910a77eec6195955b780484642f9afb8f1edc2003a9e3ef5cbb28f` |
| Isi `thesis_pooled_results.csv` (setelah dekompresi) | `e62474f2f9a15b5fd213cf7cbbd00d8750b290cff51f08459858b64844ca2641` |

Hash berkas mentah di `LOCK.json` memuat stempel waktu (field waktu JSON dan header gzip), sehingga
yang dibandingkan saat reproduksi adalah hash di atas. Satu run penuh
(`python -m scripts.thesis_analysis --force`) memakan waktu ±2,1 jam pada laptop pengembangan (sebagian
besar untuk pemilihan K berbasis stabilitas; komputer tidak boleh sleep). Determinisme diperiksa dengan
dua run yang menghasilkan hash identik. Hasil lama diarsipkan di `data/locked/arsip_v1/` dan
`data/locked/arsip_v2/` (tag `hasil-skripsi-v1`, `hasil-skripsi-v2`).

K model utama untuk tabel Bab IV dan dashboard diatur di `pengaturan_hasil.json`
(`python -m scripts.export_bab4 --k-utama 2` untuk menukar tanpa mengubah berkas).

Menjalankan ulang analisis dan mengunci hasil baru mengikuti `docs/ALUR_KERJA.md`. Semua angka
skripsi diambil dari `output_bab4/` (tabel CSV, `Tabel_Bab4.docx`, `ringkasan_angka_bab4.md`,
`perbandingan_v2_vs_v3.md`). Metode lengkap ada di `docs/METODOLOGI.md`; diagnostik sumber
kelas bahaya di `docs/DIAGNOSTIK_JALAN_GRID.md`.

## Membagikan secara online

Lihat `docs/DEPLOY.md` (Cloudflare Tunnel, gratis tanpa akun).

## Sumber data

Grid analisis dan atribut aksesibilitas (hasil penelitian), jaringan jalan, sebaran TES,
indeks bahaya banjir, serta batas administrasi desa/kelurahan (Badan Informasi Geospasial,
skala 1:10.000). Peta dasar © Esri & OpenStreetMap contributors; pencarian alamat
© OpenStreetMap contributors (Photon, Nominatim).

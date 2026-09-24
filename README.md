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
python -m scripts.cek_reproduksi           # jalankan ulang ke folder sementara + bandingkan hash (±1,7 jam)
python -m scripts.export_bab4              # bangun ulang output_bab4/ dari data/locked/ (beberapa detik)
```

Hash yang diharapkan (hasil `hasil-skripsi-v2`, desain gabungan, K = 2):

| Besaran | SHA-256 |
|---|---|
| Fingerprint `thesis_results.json` tanpa field waktu dan `meta.git` | `565eff44f3264717d49bea0cf028f9f46337932a9d22ca3814302697c71a314a` |
| Isi `thesis_grid_results.csv` (setelah dekompresi) | `98bec16c545d8c2a987439ff7145fa32f47150eafce2d08093678c987ed0ce7e` |
| Isi `thesis_pooled_results.csv` (setelah dekompresi) | `02815cd0bfd48766bb72d9eda6b1ba4413d6343fda198e9d904c96404734b820` |

Hash berkas mentah di `LOCK.json` memuat stempel waktu (field waktu JSON dan header gzip), sehingga
yang dibandingkan saat reproduksi adalah hash di atas. Satu run penuh
(`python -m scripts.thesis_analysis --force`) memakan waktu ±1,7 jam pada laptop pengembangan (sebagian
besar untuk pemilihan K berbasis stabilitas). Determinisme diperiksa dengan dua run yang menghasilkan
hash identik. Hasil v1 diarsipkan di `data/locked/arsip_v1/` (tag `hasil-skripsi-v1`).

Menjalankan ulang analisis dan mengunci hasil baru mengikuti `docs/ALUR_KERJA.md`. Semua angka
skripsi diambil dari `output_bab4/` (tabel CSV, `Tabel_Bab4.docx`, `ringkasan_angka_bab4.md`,
`perbandingan_v1_vs_v2.md`). Metode lengkap ada di `docs/METODOLOGI.md`.

## Membagikan secara online

Lihat `docs/DEPLOY.md` (Cloudflare Tunnel, gratis tanpa akun).

## Sumber data

Grid analisis dan atribut aksesibilitas (hasil penelitian), jaringan jalan, sebaran TES,
indeks bahaya banjir, serta batas administrasi desa/kelurahan (Badan Informasi Geospasial,
skala 1:10.000). Peta dasar © Esri & OpenStreetMap contributors; pencarian alamat
© OpenStreetMap contributors (Photon, Nominatim).

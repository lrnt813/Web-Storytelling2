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
python -m scripts.cek_reproduksi           # jalankan ulang ke folder sementara + bandingkan hash (±9 menit)
python -m scripts.export_bab4              # bangun ulang output_bab4/ dari data/locked/ (beberapa detik)
```

Hash yang diharapkan (hasil `hasil-skripsi-v4`: keluaran K = 2, 3, 4; TAS dengan syarat T_aktual ≥ 30 menit;
kategori akses):

| Besaran | SHA-256 |
|---|---|
| Fingerprint `thesis_results.json` tanpa field waktu dan `meta.git` | `f3081907c8e50c72c982470aabb4d5d36fdbbcb0a230a96d0173c3fe329bd4d4` |
| Isi `thesis_grid_results.csv` (setelah dekompresi) | `ca705355f0a47d78e8c4c6200b13562a3e08625bcfae5da0b866922c6067f80a` |
| Isi `thesis_pooled_results.csv` (setelah dekompresi) | `398451698bd772f376025f974c63445d9e228b04c4f95349d4c34d41779426f4` |

Hash berkas mentah di `LOCK.json` memuat stempel waktu (field waktu JSON dan header gzip), sehingga
yang dibandingkan saat reproduksi adalah hash di atas. Pada v4, pemilihan K tidak dijalankan ulang:
tabel stabilitas diambil dari `data/locked/arsip_v3/` setelah data gabungan diverifikasi identik.
Satu run penuh memakan waktu ±9 menit. Determinisme diperiksa dengan dua run yang menghasilkan hash
identik. Hasil lama diarsipkan di `data/locked/arsip_v1/`, `arsip_v2/`, dan `arsip_v3/`.

K model utama untuk tabel Bab IV dan dashboard diatur di `pengaturan_hasil.json`
(`python -m scripts.export_bab4 --k-utama 2` untuk menukar tanpa mengubah berkas).

Menjalankan ulang analisis dan mengunci hasil baru mengikuti `docs/ALUR_KERJA.md`. Semua angka
skripsi diambil dari `output_bab4/` (tabel CSV, `Tabel_Bab4.docx`, `ringkasan_angka_bab4.md`,
`perbandingan_v3_vs_v4.md`). Metode lengkap ada di `docs/METODOLOGI.md`, rujukan parameter di
`docs/RUJUKAN_PARAMETER.md`; diagnostik sumber
kelas bahaya di `docs/DIAGNOSTIK_JALAN_GRID.md`.

## Membagikan secara online

Lihat `docs/DEPLOY.md` (Cloudflare Tunnel, gratis tanpa akun).

## Sumber data

Grid analisis dan atribut aksesibilitas (hasil penelitian), jaringan jalan, sebaran TES,
indeks bahaya banjir, serta batas administrasi desa/kelurahan (Badan Informasi Geospasial,
skala 1:10.000). Peta dasar © Esri & OpenStreetMap contributors; pencarian alamat
© OpenStreetMap contributors (Photon, Nominatim).

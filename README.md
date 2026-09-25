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

**Hasil final: `hasil-skripsi-v6`** (snapping ke ruas terdekat; kelas bahaya dari raster InaRisk; TAS dengan
syarat T_aktual ≥ 30 menit; kategori akses; atribusi banjir pada TAS). Keluaran Bab IV v6 (`output_bab4/`)
dibangun dengan **`k_utama = 4`** (keputusan final atas dasar substantif; METODOLOGI §9 (h),
`docs/KEPUTUSAN_K_v6.md`); K = 2 dan K = 3 sebagai sensitivitas. Keluaran Bab IV final diberi tag
**`bab4-final`**. Analisis dinyatakan final; perubahan berikutnya hanya pengisian validasi TAS dan rekapnya
(`docs/CATATAN_TEMUAN.md`, "Penutupan analisis"). Hash yang diharapkan:

| Besaran | SHA-256 |
|---|---|
| Fingerprint `thesis_results.json` tanpa field waktu dan `meta.git` | `e58b6e7e7814fc8d8e08f90ae64495da4f3259aeae1e4837c8de0995e9481a00` |
| Isi `thesis_grid_results.csv` (setelah dekompresi) | `9e9dc36860e7d57c873e9fee2f0b46e59bea623601342cadae1da974544f4de0` |
| Isi `thesis_pooled_results.csv` (setelah dekompresi) | `d4ea0ec5eba98ff9748fd6466a7de9e71a4e61354f7d868e60db0253a981c6f9` |

Hash berkas mentah di `LOCK.json` memuat stempel waktu (field waktu JSON dan header gzip), sehingga
yang dibandingkan saat reproduksi adalah hash di atas. Pemilihan K (stabilitas) dihitung ulang pada data v6;
satu run penuh memakan waktu ±1 jam 46 menit. Determinisme diperiksa dengan dua run yang menghasilkan hash
identik. Hasil lama diarsipkan di `data/locked/arsip_v1/` sampai `arsip_v5/`.

Metrik Finalisasi v6 (DESC-N/PESC-N, perbandingan dengan SDWFCM versi asli Guo dkk., validasi data buatan) ada di
`output_bab4/finalisasi_v6/` dan dibuat dengan `python -m scripts.reproduksi_label_v6`,
`python -m scripts.validasi_desc_n_sintetis`, lalu `python -m scripts.metrik_finalisasi_v6`; hasil terkunci
tidak berubah.

Validasi manual TAS: isi `output_bab4/validasi/validasi_TAS_v6.xlsx` (dibuat oleh
`python -m scripts.lembar_validasi_TAS`), lalu jalankan `python -m scripts.rekap_validasi_TAS`.

K model utama untuk tabel Bab IV dan dashboard diatur di `pengaturan_hasil.json`
(`python -m scripts.export_bab4 --k-utama 2` untuk menukar tanpa mengubah berkas).

Menjalankan ulang analisis dan mengunci hasil baru mengikuti `docs/ALUR_KERJA.md`. Semua angka
skripsi diambil dari `output_bab4/` (tabel CSV, `Tabel_Bab4.docx`, `ringkasan_angka_bab4.md`,
`temuan_kunci.md`, `perbandingan_v5_vs_v6.md`). Metode lengkap ada di `docs/METODOLOGI.md`, rujukan parameter di
`docs/RUJUKAN_PARAMETER.md`; diagnostik sumber
kelas bahaya di `docs/DIAGNOSTIK_JALAN_GRID.md`.

## Membagikan secara online

Lihat `docs/DEPLOY.md` (Cloudflare Tunnel, gratis tanpa akun).

## Sumber data

Grid analisis dan atribut aksesibilitas (hasil penelitian), jaringan jalan, sebaran TES,
indeks bahaya banjir, serta batas administrasi desa/kelurahan (Badan Informasi Geospasial,
skala 1:10.000). Peta dasar © Esri & OpenStreetMap contributors; pencarian alamat
© OpenStreetMap contributors (Photon, Nominatim).

---
title: Aksesibilitas TES Banjir Kulon Progo
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Dashboard SDWFCM aksesibilitas TES banjir
---

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
python start_dashboard.py          # membuka http://127.0.0.1:8000
```

Hasil analisis sudah tersedia dan dikunci di `data/locked/`. Untuk menghitung ulang:
`python -m scripts.thesis_analysis --force` (perlu paket opsional di `requirements.txt`).

## Deploy ke Hugging Face Spaces

Lihat `docs/DEPLOY.md`.

## Sumber data

Grid analisis dan atribut aksesibilitas (hasil penelitian), jaringan jalan, sebaran TES,
indeks bahaya banjir, serta batas administrasi desa/kelurahan (Badan Informasi Geospasial,
skala 1:10.000). Peta dasar © Esri & OpenStreetMap contributors; pencarian alamat
© OpenStreetMap contributors (Photon, Nominatim).

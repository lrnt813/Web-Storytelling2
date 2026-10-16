# Panduan Penggunaan

Panduan ini untuk memasang, menjalankan, dan memakai dashboard Aksesibilitas TES Banjir Kulon Progo,
serta menjalankan ulang pemodelan.

## 1. Kebutuhan

- Windows, Linux, atau macOS; RAM minimal 4 GB (server memakai ± 1,5 GB).
- Python **3.14** (`.python-version`; versi lain mungkin berjalan tetapi tidak dijamin hasilnya identik).
- Git dan **Git LFS** (untuk mengunduh berkas GeoPackage).
- Browser modern (Chrome, Edge, Firefox). Internet diperlukan untuk peta dasar, ikon, dan pencarian alamat.

## 2. Instalasi

```bash
git clone <URL-REPOSITORI>
cd <nama-folder>
git lfs pull                       # pastikan data/*.gpkg berukuran MB, bukan pointer teks
python -m venv .venv
.venv\Scripts\activate             # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

## 3. Menjalankan dashboard

```bash
python start_dashboard.py
```

Buka `http://127.0.0.1:8000`. Di Windows bisa juga klik dua kali `Jalankan Dashboard.bat`. Pemuatan
pertama memerlukan ± 1–2 menit karena server membangun graf jalan (berikutnya lebih cepat karena cache di
`scratch/`). Hentikan dengan `Ctrl+C`.

Opsional, untuk memberi alamat publik sementara (mis. saat sidang): `python start_dashboard.py --publik`
atau `Jalankan Dashboard Publik.bat` (Cloudflare Tunnel; lihat `docs/DEPLOY.md`).

Alternatif dengan Docker: `docker build -t dashboard-tes .` lalu `docker run -p 7860:7860 dashboard-tes`,
buka `http://127.0.0.1:7860`.

## 4. Memakai dashboard

### 4.1 Panel kiri: skenario dan tampilan

1. **Level Banjir.** Pilih Baseline, Rendah (kelas bahaya 3 ditutup), Sedang (kelas ≥ 2), atau Tinggi
   (kelas ≥ 1). Grid dan ruas jalan pada kelas yang ditutup dianggap tergenang dan tidak dapat dilalui.
2. **Jumlah klaster (K).** Bawaan K = 4 (model utama); K = 2 dan K = 3 untuk sensitivitas.
3. **Tampilan Peta.** Pilih salah satu:
   - *Tipologi Klaster SDWFCM*: warna tipologi; label berisi kombinasi akses dan jaringan jalan;
   - *Titik Aman Semu (TAS)*: grid yang dekat TES secara garis lurus tetapi jauh lewat jalan;
   - *Grid Tergenang*;
   - *Kategori Akses (batas 30 menit)*;
   - *Waktu Tempuh Minimum ke TES*;
   - *Indeks Bahaya Banjir*.
4. **Bandingkan dengan level.** Pilih level kedua, lalu geser pembatas di peta untuk membandingkan kiri
   dan kanan.

Legenda di peta menyesuaikan tampilan yang aktif.

### 4.2 Info Grid dan rute evakuasi

Pada tab **Simulasi Lapangan → Info Grid**, klik sebuah grid. Popup menampilkan tipologi dan derajat
keanggotaan, waktu tempuh ke setiap kategori TES, status TAS, kategori akses, serta kalurahan dan
kapanewon. Rute evakuasi optimal ke TES terdekat digambar di peta. Waktu dihitung dengan kecepatan
berjalan kaki 80 m/menit.

### 4.3 Simulasi blokir jalan

1. Buka tab **Blokir Jalan**. Centang *Tampilkan jaringan jalan* agar ruas terlihat.
2. Klik ruas jalan yang ingin diputus. Klik di luar jaringan jalan ditolak dengan pemberitahuan.
   Klik penanda untuk membatalkan satu blokir.
3. Tekan **Terapkan Blokir**. Server menghitung ulang waktu tempuh dan tipologi (± 15 detik).
   Muncul pita **MODE SIMULASI**: hasil ini bukan hasil skripsi.
4. Kembali ke **Info Grid** untuk melihat detail grid hasil simulasi.
5. **Reset** menghapus semua blokir; **Kembali ke hasil skripsi** menampilkan hasil terkunci lagi.

### 4.4 Pencarian

Kotak pencarian di atas peta menerima nama kapanewon, kalurahan, alamat, atau tempat. Tombol lokasi
memakai GPS perangkat (izinkan akses lokasi di browser). Batas kabupaten, kapanewon, dan kalurahan dapat
ditampilkan dari kontrol batas wilayah.

### 4.5 Prioritas Wilayah

Tombol **PRIORITAS WILAYAH** membuka ringkasan per kalurahan atau kapanewon pada level aktif: jumlah grid,
% grid terisolasi, jumlah TAS, % grid tergenang, rata-rata waktu minimum, dan komposisi tipologi. Urutkan
dengan menu *Urutkan prioritas*; klik baris untuk menyorot wilayah di peta.

### 4.6 Hasil Penelitian

Tombol **HASIL PENELITIAN** membuka tabel dan grafik Bab IV dalam tab: Data & Statistik, Pemilihan K,
Perbandingan Algoritma, Profil Klaster, Transisi Klaster (matriks dan diagram Sankey), Titik Aman Semu,
dan Waktu Tempuh. Setiap tabel dapat diunduh (Excel), setiap grafik dapat diunduh (PNG); tersedia juga
**Unduh semua tabel** dan **Unduh data grid**.

## 5. Menjalankan ulang pemodelan

```bash
python -m pytest -q                         # uji unit (± 1 menit)
python -m scripts.cek_reproduksi            # jalankan ulang pipeline ke folder sementara dan bandingkan hash (± 2 jam; termasuk pemilihan K)
python -m scripts.export_bab4               # bangun ulang output_bab4/ dari hasil terkunci (beberapa detik)
```

- Analisis penuh termasuk pemilihan K: `python -m scripts.thesis_analysis --force` (± 1 jam 46 menit).
  Hasil ditulis ke `data/thesis_*`; hasil terkunci di `data/locked/` tidak berubah sampai dikunci ulang
  sesuai `docs/ALUR_KERJA.md`.
- K utama tabel Bab IV dan dashboard diatur di `pengaturan_hasil.json`.
- Peta sebaran penduduk per desa: `python -m scripts.penduduk_desa --hanya-peta`.
- Validasi manual TAS: `python -m scripts.lembar_validasi_TAS` (membuat lembar Excel), isi lembar, lalu
  `python -m scripts.rekap_validasi_TAS`. Untuk membuat ulang peta validasi saja tanpa menimpa lembar yang sudah
  diisi: `python -m scripts.lembar_validasi_TAS --hanya-peta`.

## 6. Masalah umum

| Gejala | Penyebab dan solusi |
|---|---|
| Error membaca `.gpkg` / berkas sangat kecil | Berkas LFS belum diunduh: jalankan `git lfs install` lalu `git lfs pull` |
| Halaman terbuka tetapi data tidak muncul | Server belum selesai memuat; tunggu, lalu muat ulang halaman |
| Windows memblokir DLL SciPy/NumPy | Smart App Control memblokir pustaka; nonaktifkan di Windows Security → App & browser control |
| Port 8000 sudah dipakai | Tutup server lain, atau jalankan `uvicorn backend.main:app --port 8001` |
| Pencarian alamat gagal | Memerlukan internet (OpenStreetMap Photon/Nominatim); pencarian kalurahan/kapanewon tetap bekerja |

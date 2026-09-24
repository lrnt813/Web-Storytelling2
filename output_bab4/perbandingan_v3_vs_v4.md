# Perbandingan angka kunci v3 vs v4

v3 = `data/locked/arsip_v3/` (tag `hasil-skripsi-v3`); v4 = `data/locked/` (tag `hasil-skripsi-v4`). **Angka v4 yang berlaku.** Data gabungan, praproses, dan pemilihan K tidak dijalankan ulang; perbedaan hanya dari perubahan penyajian dan aturan TAS.

| Angka | v3 | v4 | Perubahan metode penyebab |
|---|---:|---:|---|
| Grid Tergenang — Baseline | 0 | 0 | Tidak berubah (data dan level sama) |
| Grid Tergenang — Rendah | 39 | 39 | Tidak berubah (data dan level sama) |
| Grid Tergenang — Sedang | 3.375 | 3.375 | Tidak berubah (data dan level sama) |
| Grid Tergenang — Tinggi | 7.175 | 7.175 | Tidak berubah (data dan level sama) |
| Rerata waktu minimum non-Tergenang — Baseline | 9,04 | 9,04 | Tidak berubah |
| Rerata waktu minimum non-Tergenang — Rendah | 9,33 | 9,33 | Tidak berubah |
| Rerata waktu minimum non-Tergenang — Sedang | 16,67 | 16,67 | Tidak berubah |
| Rerata waktu minimum non-Tergenang — Tinggi | 24,41 | 24,41 | Tidak berubah |
| Baris data gabungan | 80.103 | 80.103 | Tidak berubah (diverifikasi identik) |
| K menurut aturan stabilitas | 2 | 2 | Pemilihan K tidak dijalankan ulang (tabel v3) |
| TAS aturan utama — Baseline | 5.758 | 62 | Aturan utama v4 menambah syarat T_aktual ≥ 30 menit (v3: DI ≥ 2 dan T_ideal ≤ 5 menit) |
| TAS aturan absolut v3 — Baseline | 5.758 | 5.758 | Sama (aturan v3 menjadi sensitivitas di v4) |
| TAS aturan persentil — Baseline | 1.842 | 1.842 | Sama |
| TAS aturan utama — Rendah | 5.757 | 70 | Aturan utama v4 menambah syarat T_aktual ≥ 30 menit (v3: DI ≥ 2 dan T_ideal ≤ 5 menit) |
| TAS aturan absolut v3 — Rendah | 5.757 | 5.757 | Sama (aturan v3 menjadi sensitivitas di v4) |
| TAS aturan persentil — Rendah | 1.811 | 1.811 | Sama |
| TAS aturan utama — Sedang | 5.092 | 77 | Aturan utama v4 menambah syarat T_aktual ≥ 30 menit (v3: DI ≥ 2 dan T_ideal ≤ 5 menit) |
| TAS aturan absolut v3 — Sedang | 5.092 | 5.092 | Sama (aturan v3 menjadi sensitivitas di v4) |
| TAS aturan persentil — Sedang | 1.485 | 1.485 | Sama |
| TAS aturan utama — Tinggi | 3.685 | 44 | Aturan utama v4 menambah syarat T_aktual ≥ 30 menit (v3: DI ≥ 2 dan T_ideal ≤ 5 menit) |
| TAS aturan absolut v3 — Tinggi | 3.685 | 3.685 | Sama (aturan v3 menjadi sensitivitas di v4) |
| TAS aturan persentil — Tinggi | 1.047 | 1.047 | Sama |
| Baris klaster 0 K = 2 | 39.147 | 39.147 | Model sama (label diverifikasi identik) |
| Baris klaster 1 K = 2 | 40.956 | 40.956 | Model sama (label diverifikasi identik) |
| Label K = 2 | Akses Baik, Akses Baik | Tipologi 1 (terbaik), Tipologi 2 (terburuk) | Label peringkat menggantikan label ambang median (P3-9) |
| Silhouette FCM (K = 2) | 0,303 | 0,303 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette SFCM (K = 2) | 0,295 | 0,295 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette SDWFCM (K = 2) | 0,296 | 0,296 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette REDCAP (K = 2) | 0,055 | 0,055 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette SKATER (K = 2) | – | – | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Baris klaster 0 K = 3 | 23.669 | 23.669 | Model sama (label diverifikasi identik) |
| Baris klaster 1 K = 3 | 34.749 | 34.749 | Model sama (label diverifikasi identik) |
| Baris klaster 2 K = 3 | 21.685 | 21.685 | Model sama (label diverifikasi identik) |
| Label K = 3 | Akses Baik, Akses Baik, Akses Sedang | Tipologi 1 (terbaik), Tipologi 2, Tipologi 3 (terburuk) | Label peringkat menggantikan label ambang median (P3-9) |
| Silhouette FCM (K = 3) | 0,194 | 0,194 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette SFCM (K = 3) | 0,161 | 0,161 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette SDWFCM (K = 3) | 0,209 | 0,209 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette REDCAP (K = 3) | 0,023 | 0,023 | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Silhouette SKATER (K = 3) | – | – | Sama (perbandingan dijalankan ulang dengan pengaturan sama) |
| Model K = 4 | – | tersedia | Baru di v4 (keluaran lengkap) |
| Kategori akses (Tergenang/Terputus/Jauh/Terjangkau) | – | tersedia | Baru di v4 (Li dkk., 2026) |
| TAS baru/hilang terhadap Baseline | – | tersedia | Baru di v4 |

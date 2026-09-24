# Perbandingan angka kunci v2 vs v3

v2 = `data/locked/arsip_v2/` (tag `hasil-skripsi-v2`); v3 = `data/locked/` (tag `hasil-skripsi-v3`). **Angka v3 yang berlaku.** Kolom terakhir = perubahan metode penyebab perbedaan.

| Angka | v2 | v3 | Perubahan metode penyebab |
|---|---:|---:|---|
| Grid Tergenang — Baseline | 0 | 0 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Grid Tergenang — Rendah | 2.531 | 39 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Grid Tergenang — Sedang | 7.845 | 3.375 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Grid Tergenang — Tinggi | 8.041 | 7.175 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Ruas ditutup — Baseline | 0 | 0 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum); aturan maksimum menaikkan kelas 2.477 ruas |
| Ruas ditutup — Rendah | 702 | 710 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum); aturan maksimum menaikkan kelas 2.477 ruas |
| Ruas ditutup — Sedang | 20.871 | 20.963 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum); aturan maksimum menaikkan kelas 2.477 ruas |
| Ruas ditutup — Tinggi | 41.619 | 44.096 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum); aturan maksimum menaikkan kelas 2.477 ruas |
| TES valid — Baseline | 1.434 | 1.434 | Kelas TES sama; aturan radius 50 m memakai grid Tergenang baru |
| TES valid — Rendah | 1.218 | 1.434 | Kelas TES sama; aturan radius 50 m memakai grid Tergenang baru |
| TES valid — Sedang | 857 | 1.367 | Kelas TES sama; aturan radius 50 m memakai grid Tergenang baru |
| TES valid — Tinggi | 849 | 989 | Kelas TES sama; aturan radius 50 m memakai grid Tergenang baru |
| T_pen (menit) | 403,87 | 403,87 | Tidak ada perubahan pada Baseline (tidak ada penutupan) |
| Rerata waktu minimum non-Tergenang — Baseline | 9,04 | 9,04 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Rerata waktu minimum non-Tergenang — Rendah | 9,84 | 9,33 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Rerata waktu minimum non-Tergenang — Sedang | 27,10 | 16,67 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Rerata waktu minimum non-Tergenang — Tinggi | 43,77 | 24,41 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Baris data gabungan | 72.275 | 80.103 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Komponen PCA | 4 | 5 | Data gabungan berubah |
| K menurut aturan stabilitas | 2 | 2 | Stabilitas K dihitung ulang pada data v3 (keputusan peneliti) |
| ARI subsampel K = 2 | 0,964 | 0,957 | Data v3 |
| ARI subsampel K = 3 | 0,963 | 0,940 | Data v3 |
| TAS — Baseline | 1.842 | 5.758 | Aturan utama v3: DI ≥ 2 dan T_ideal ≤ 5 menit (v2: persentil P25/P75) + Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS aturan persentil — Baseline | 1.842 | 1.842 | Aturan sama (persentil); perbedaan karena Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Terputus — Baseline | 168 | 168 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS — Rendah | 1.652 | 5.757 | Aturan utama v3: DI ≥ 2 dan T_ideal ≤ 5 menit (v2: persentil P25/P75) + Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS aturan persentil — Rendah | 1.652 | 1.811 | Aturan sama (persentil); perbedaan karena Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Terputus — Rendah | 162 | 182 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS — Sedang | 1.042 | 5.092 | Aturan utama v3: DI ≥ 2 dan T_ideal ≤ 5 menit (v2: persentil P25/P75) + Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS aturan persentil — Sedang | 1.042 | 1.485 | Aturan sama (persentil); perbedaan karena Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Terputus — Sedang | 819 | 600 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS — Tinggi | 958 | 3.685 | Aturan utama v3: DI ≥ 2 dan T_ideal ≤ 5 menit (v2: persentil P25/P75) + Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| TAS aturan persentil — Tinggi | 958 | 1.047 | Aturan sama (persentil); perbedaan karena Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Terputus — Tinggi | 1.576 | 951 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Stability rate K = 2 Baseline → Rendah (%) | 93,33 | 99,78 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| ARI K = 2 Baseline → Rendah | 0,742 | 0,991 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Stability rate K = 2 Rendah → Sedang (%) | 79,74 | 92,25 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| ARI K = 2 Rendah → Sedang | 0,354 | 0,714 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Stability rate K = 2 Sedang → Tinggi (%) | 85,65 | 82,86 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| ARI K = 2 Sedang → Tinggi | 0,508 | 0,432 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Stability rate K = 2 Baseline → Tinggi (%) | 59,58 | 76,91 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| ARI K = 2 Baseline → Tinggi | 0,012 | 0,289 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Silhouette FCM (K = 2) | 0,325 | 0,303 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Silhouette SFCM (K = 2) | 0,317 | 0,295 | m SFCM 2,0 → 1,7 + Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Silhouette SDWFCM (K = 2) | 0,319 | 0,296 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Silhouette REDCAP (K = 2) | 0,060 | 0,055 | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |
| Silhouette SKATER (K = 2) | – | – | Kelas bahaya dari raster InaRisk (grid mayoritas piksel, ruas maksimum) |

Perubahan metode v3 lainnya (tidak mengubah angka di atas secara langsung): label interpretasi berbasis median dan proporsi penalti; PC/PE; tabel K utama/lampiran; keluaran lengkap K = 2 dan K = 3.

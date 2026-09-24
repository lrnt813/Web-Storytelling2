# Perbandingan angka kunci v1 vs v2

v1 = `data/locked/arsip_v1/` (tag `hasil-skripsi-v1`); v2 = `data/locked/` (tag `hasil-skripsi-v2`). **Angka v2 yang berlaku.** Kolom terakhir menyebut perubahan metode (putaran 2) yang menyebabkan perbedaan.

| Angka | v1 | v2 | Perubahan metode penyebab |
|---|---:|---:|---|
| T_pen (menit) | 402,26 | 403,87 | Langkah 3: waktu tempuh memuat ruas snapping (T_max Baseline berubah) |
| Rata-rata waktu minimum Baseline (menit) | 8,16 | 9,04 | Langkah 3: ruas snapping |
| Median waktu minimum Baseline (menit) | 4,96 | 5,81 | Langkah 3: ruas snapping |
| Jumlah fitur klasterisasi | 10 | 9 | Langkah 5: kelas bahaya banjir bukan fitur |
| Komponen PCA | 5 | 4 | Langkah 5 + 6: 9 fitur, praproses di-fit pada data gabungan (bukan Baseline) |
| Varians kumulatif PCA (%) | 85,19 | 81,00 | Langkah 5 + 6 |
| K terpilih | 4 | 2 | Langkah 7: aturan stabilitas subsampel menggantikan skor komposit; Langkah 6: data gabungan |
| Grid terdampak/Tergenang — Baseline | 0 | 0 | Tidak ada perubahan himpunan (Langkah 2 membuktikan aturan kelas = aturan intensitas lama) |
| Ruas ditutup — Baseline | 0 | 0 | Sama (Langkah 2) |
| TES valid — Baseline | 1.434 | 1.434 | Sama (aturan TES tidak diubah) |
| Grid terdampak/Tergenang — Rendah | 2.531 | 2.531 | Tidak ada perubahan himpunan (Langkah 2 membuktikan aturan kelas = aturan intensitas lama) |
| Ruas ditutup — Rendah | 702 | 702 | Sama (Langkah 2) |
| TES valid — Rendah | 1.218 | 1.218 | Sama (aturan TES tidak diubah) |
| Grid terdampak/Tergenang — Sedang | 7.845 | 7.845 | Tidak ada perubahan himpunan (Langkah 2 membuktikan aturan kelas = aturan intensitas lama) |
| Ruas ditutup — Sedang | 20.871 | 20.871 | Sama (Langkah 2) |
| TES valid — Sedang | 857 | 857 | Sama (aturan TES tidak diubah) |
| Grid terdampak/Tergenang — Tinggi | 8.041 | 8.041 | Tidak ada perubahan himpunan (Langkah 2 membuktikan aturan kelas = aturan intensitas lama) |
| Ruas ditutup — Tinggi | 41.619 | 41.619 | Sama (Langkah 2) |
| TES valid — Tinggi | 849 | 849 | Sama (aturan TES tidak diubah) |
| Rata-rata waktu minimum — Baseline (menit) | 8,16 | 9,04 | Langkah 3 (ruas snapping) + Langkah 4 (v2: rata-rata grid non-Tergenang; v1: semua grid) |
| Rata-rata waktu minimum — Rendah (menit) | 9,29 | 9,84 | Langkah 3 (ruas snapping) + Langkah 4 (v2: rata-rata grid non-Tergenang; v1: semua grid) |
| Rata-rata waktu minimum — Sedang (menit) | 51,67 | 27,10 | Langkah 3 (ruas snapping) + Langkah 4 (v2: rata-rata grid non-Tergenang; v1: semua grid) |
| Rata-rata waktu minimum — Tinggi (menit) | 105,70 | 43,77 | Langkah 3 (ruas snapping) + Langkah 4 (v2: rata-rata grid non-Tergenang; v1: semua grid) |
| TAS — Baseline | 1.415 | 1.842 | Langkah 3 (T_aktual memuat ruas snapping, batas 50 m di kedua jarak) + Langkah 4 (grid Tergenang dikeluarkan dari persentil) |
| Terputus — Baseline | 168 | 168 | Langkah 4: v1 Terputus mencakup grid terdampak; v2 grid tersebut berstatus Tergenang |
| Rerata DI TAS — Baseline | 3,925 | 4,214 | Langkah 3 + 4 |
| Rerata DI Non-TAS — Baseline | 1,619 | 1,923 | Langkah 3 + 4 |
| TAS — Rendah | 1.438 | 1.652 | Langkah 3 (T_aktual memuat ruas snapping, batas 50 m di kedua jarak) + Langkah 4 (grid Tergenang dikeluarkan dari persentil) |
| Terputus — Rendah | 182 | 162 | Langkah 4: v1 Terputus mencakup grid terdampak; v2 grid tersebut berstatus Tergenang |
| Rerata DI TAS — Rendah | 3,812 | 4,156 | Langkah 3 + 4 |
| Rerata DI Non-TAS — Rendah | 1,614 | 1,912 | Langkah 3 + 4 |
| TAS — Sedang | 1.136 | 1.042 | Langkah 3 (T_aktual memuat ruas snapping, batas 50 m di kedua jarak) + Langkah 4 (grid Tergenang dikeluarkan dari persentil) |
| Terputus — Sedang | 3.078 | 819 | Langkah 4: v1 Terputus mencakup grid terdampak; v2 grid tersebut berstatus Tergenang |
| Rerata DI TAS — Sedang | 3,997 | 4,347 | Langkah 3 + 4 |
| Rerata DI Non-TAS — Sedang | 1,910 | 1,976 | Langkah 3 + 4 |
| TAS — Tinggi | 935 | 958 | Langkah 3 (T_aktual memuat ruas snapping, batas 50 m di kedua jarak) + Langkah 4 (grid Tergenang dikeluarkan dari persentil) |
| Terputus — Tinggi | 6.316 | 1.576 | Langkah 4: v1 Terputus mencakup grid terdampak; v2 grid tersebut berstatus Tergenang |
| Rerata DI TAS — Tinggi | 4,548 | 4,873 | Langkah 3 + 4 |
| Rerata DI Non-TAS — Tinggi | 1,887 | 2,053 | Langkah 3 + 4 |
| Stability rate Baseline → Rendah (%) | 74,46 | 93,33 | Langkah 6 (satu model gabungan, tanpa Hungarian) + Langkah 10 (dihitung pada grid non-Tergenang di kedua level) |
| ARI Baseline → Rendah | 0,453 | 0,742 | Langkah 6 + 10 |
| Stability rate Rendah → Sedang (%) | 39,12 | 79,74 | Langkah 6 (satu model gabungan, tanpa Hungarian) + Langkah 10 (dihitung pada grid non-Tergenang di kedua level) |
| ARI Rendah → Sedang | 0,119 | 0,354 | Langkah 6 + 10 |
| Stability rate Sedang → Tinggi (%) | 43,01 | 85,65 | Langkah 6 (satu model gabungan, tanpa Hungarian) + Langkah 10 (dihitung pada grid non-Tergenang di kedua level) |
| ARI Sedang → Tinggi | 0,156 | 0,508 | Langkah 6 + 10 |
| Stability rate Baseline → Tinggi (%) | – | 59,58 | Langkah 6 (satu model gabungan, tanpa Hungarian) + Langkah 10 (dihitung pada grid non-Tergenang di kedua level); pasangan baru di v2 |
| ARI Baseline → Tinggi | – | 0,012 | Langkah 6 + 10; pasangan baru di v2 |
| Silhouette FCM | – | 0,325 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; algoritma baru di v2 |
| Moran's I FCM | – | 0,768 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; algoritma baru di v2; Moran 999 permutasi (v1: 99) |
| Silhouette SFCM | 0,052 | 0,317 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5) |
| Moran's I SFCM | 0,871 | 0,783 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5); Moran 999 permutasi (v1: 99) |
| Silhouette SDWFCM | 0,163 | 0,319 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5) |
| Moran's I SDWFCM | 0,857 | 0,832 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5); Moran 999 permutasi (v1: 99) |
| Silhouette REDCAP | -0,046 | 0,060 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5) |
| Moran's I REDCAP | 1,000 | 1,000 | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5); Moran 999 permutasi (v1: 99) |
| Status REDCAP | dilaporkan tanpa penanda | degeneratif | Langkah 8: penanda degeneratif (> 90 %) |
| Silhouette SKATER | 0,773 | – | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5) |
| Moran's I SKATER | 0,833 | – | Langkah 8: Baseline dengan praproses gabungan, K baru, 10 inisialisasi; fitur 9 (Langkah 5); Moran 999 permutasi (v1: 99) |
| Status SKATER | fallback MST manual | gagal | Langkah 8: spopt `floor`, fallback dihapus |

Catatan: nomor klaster v1 dan v2 tidak dapat dipasangkan satu-satu (v1: model per level + Hungarian; v2: satu model gabungan), sehingga profil per klaster tidak dibandingkan per nomor.

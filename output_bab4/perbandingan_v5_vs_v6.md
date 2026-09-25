# Perbandingan angka kunci v5 vs v6

v5 = `data/locked/arsip_v5/` (tag `hasil-skripsi-v5`); v6 = `data/locked/` (tag `hasil-skripsi-v6`). Satu-satunya perubahan metode Putaran 6 adalah koreksi snapping: grid dan TES di-snap ke titik terdekat pada ruas jalan terbuka (simpul virtual), bukan ke verteks terdekat (CATATAN P6-1, METODOLOGI §4). Karena data gabungan berubah, pemilihan K dihitung ulang dengan aturan yang sama. Semua ambang, seed, dan aturan lain sama. Atribusi banjir pada TAS adalah keluaran baru v6 (tidak ada padanan v5). Rincian dampak snapping: `docs/DAMPAK_KOREKSI_SNAPPING.md`.

| Angka | v5 | v6 | Sumber perbedaan |
|---|---:|---:|---|
| T_pen (menit) | 403,87 | 403,29 | Koreksi snapping; aturan sama (3 × waktu maksimum valid di Baseline) |
| Baris data gabungan | 80.103 | 80.103 | Tidak bergantung snapping (grid non-Tergenang) |
| Grid Tergenang — Baseline | 0 | 0 | Tidak bergantung snapping |
| TAS utama — Baseline | 62 | 68 | Koreksi snapping (ruas terdekat, P6-1) |
| TES terdekat tidak terjangkau — Baseline | 168 | 157 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terjangkau (30 menit) — Baseline | 22.357 | 22.371 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Jauh (30 menit) — Baseline | 205 | 202 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terputus (30 menit) — Baseline | 111 | 100 | Koreksi snapping (ruas terdekat, P6-1) |
| Median waktu minimum non-Tergenang (menit) — Baseline | 5,81 | 5,69 | Koreksi snapping (ruas terdekat, P6-1) |
| Rerata waktu minimum non-Tergenang (menit) — Baseline | 9,04 | 8,73 | Koreksi snapping (ruas terdekat, P6-1) |
| Grid Tergenang — Rendah | 39 | 39 | Tidak bergantung snapping |
| TAS utama — Rendah | 70 | 76 | Koreksi snapping (ruas terdekat, P6-1) |
| TES terdekat tidak terjangkau — Rendah | 182 | 171 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terjangkau (30 menit) — Rendah | 22.254 | 22.269 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Jauh (30 menit) — Rendah | 254 | 250 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terputus (30 menit) — Rendah | 126 | 115 | Koreksi snapping (ruas terdekat, P6-1) |
| Median waktu minimum non-Tergenang (menit) — Rendah | 5,80 | 5,69 | Koreksi snapping (ruas terdekat, P6-1) |
| Rerata waktu minimum non-Tergenang (menit) — Rendah | 9,33 | 9,02 | Koreksi snapping (ruas terdekat, P6-1) |
| TAS baru akibat banjir — Rendah | 8 | 8 | Koreksi snapping (ruas terdekat, P6-1) |
| Grid Tergenang — Sedang | 3.375 | 3.375 | Tidak bergantung snapping |
| TAS utama — Sedang | 77 | 76 | Koreksi snapping (ruas terdekat, P6-1) |
| TES terdekat tidak terjangkau — Sedang | 600 | 593 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terjangkau (30 menit) — Sedang | 18.732 | 18.732 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Jauh (30 menit) — Sedang | 64 | 61 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terputus (30 menit) — Sedang | 502 | 505 | Koreksi snapping (ruas terdekat, P6-1) |
| Median waktu minimum non-Tergenang (menit) — Sedang | 5,48 | 5,34 | Koreksi snapping (ruas terdekat, P6-1) |
| Rerata waktu minimum non-Tergenang (menit) — Sedang | 16,67 | 16,59 | Koreksi snapping (ruas terdekat, P6-1) |
| TAS baru akibat banjir — Sedang | 54 | 53 | Koreksi snapping (ruas terdekat, P6-1) |
| Grid Tergenang — Tinggi | 7.175 | 7.175 | Tidak bergantung snapping |
| TAS utama — Tinggi | 44 | 44 | Koreksi snapping (ruas terdekat, P6-1) |
| TES terdekat tidak terjangkau — Tinggi | 951 | 939 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terjangkau (30 menit) — Tinggi | 14.529 | 14.544 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Jauh (30 menit) — Tinggi | 318 | 314 | Koreksi snapping (ruas terdekat, P6-1) |
| Akses Terputus (30 menit) — Tinggi | 651 | 640 | Koreksi snapping (ruas terdekat, P6-1) |
| Median waktu minimum non-Tergenang (menit) — Tinggi | 6,29 | 6,17 | Koreksi snapping (ruas terdekat, P6-1) |
| Rerata waktu minimum non-Tergenang (menit) — Tinggi | 24,41 | 24,00 | Koreksi snapping (ruas terdekat, P6-1) |
| TAS baru akibat banjir — Tinggi | 27 | 27 | Koreksi snapping (ruas terdekat, P6-1) |
| Terjangkau Baseline → Terputus Sedang | 360 | 375 | Koreksi snapping (ruas terdekat, P6-1) |
| Terjangkau Baseline → Terputus Tinggi | 555 | 553 | Koreksi snapping (ruas terdekat, P6-1) |
| ARI subsampel K = 2 | 0,957 | 0,959 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 3 | 0,940 | 0,942 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 4 | 0,949 | 0,948 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 5 | 0,940 | 0,943 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 6 | 0,809 | 0,815 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 7 | 0,926 | 0,916 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 8 | 0,878 | 0,899 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 9 | 0,635 | 0,722 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| ARI subsampel K = 10 | 0,592 | 0,812 | v5: tabel stabilitas v3 (data v3 = data v5); v6: dihitung ulang pada data v6 |
| K dalam toleransi stabilitas | 2, 4 | 2 | Dihitung ulang pada data v6 |
| K terpilih aturan (pemecah seri K terkecil) | 2 | 2 | Dihitung ulang pada data v6 |
| Baris Tipologi 1 (K = 4) | 20.397 | 20.432 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Median waktu minimum Tipologi 1 (K = 4, menit) | 3,44 | 3,29 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Baris Tipologi 2 (K = 4) | 27.069 | 27.019 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Median waktu minimum Tipologi 2 (K = 4, menit) | 4,28 | 4,16 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Baris Tipologi 3 (K = 4) | 31.215 | 31.263 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Median waktu minimum Tipologi 3 (K = 4, menit) | 9,89 | 9,76 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Baris Tipologi 4 (K = 4) | 1.422 | 1.389 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Median waktu minimum Tipologi 4 (K = 4, menit) | 403,87 | 403,29 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Silhouette (sampel) K = 4 | 0,203 | 0,201 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Ketegasan partisi K = 4 | 0,456 | 0,457 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |
| Klaster terbesar (%) K = 4 | 38,969 | 39,029 | Koreksi snapping mengubah data gabungan; model di-fit ulang (aturan sama) |

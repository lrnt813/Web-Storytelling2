# Catatan Temuan Rekonstruksi

Hal-hal janggal yang ditemukan selama rekonstruksi pipeline. Temuan yang **tidak**
termasuk perubahan yang diminta dicatat di sini dan **tidak diperbaiki diam-diam**.
Status: *DIPERBAIKI* (termasuk perubahan yang diminta), *DICATAT* (perlu keputusan).

## A. Pilihan metode yang sebelumnya dikalibrasi agar cocok dengan draft lama

Sebelum rekonstruksi, beberapa pilihan diambil dengan membandingkan keluaran
terhadap angka draft lama. Pilihan yang tidak diatur ulang oleh instruksi
rekonstruksi dibiarkan apa adanya, tetapi perlu diputuskan secara metodologis:

- **A1. Blok spasial DESC/PESC memakai ketetanggaan *queen* murni** (`thesis.queen_adjacency`),
  sedangkan matriks bobot W, Moran's I, dan metrik lain memakai *rook*. Pilihan queen diambil
  karena menghasilkan DESC K = 6 yang sama dengan draft. — *DICATAT*
- **A2. I-Index memakai pusat klaster fuzzy** (bobot u^m) alih-alih centroid tegas. — *DICATAT*
- **A3. Ketegasan partisi (1 − PE/ln K) dihitung dari keanggotaan yang dihitung ulang di ruang
  atribut** (rumus FCM tanpa suku spasial pada pusat fuzzy akhir), bukan dari U SDWFCM. — *DICATAT*
- **A4. Dunn titik-ke-titik dihitung pada sampel 2.000 grid** (RandomState(42).permutation);
  ukuran sampel dipilih karena memberi besaran yang mirip draft. — *DICATAT*
- **A5. T_aktual pada Detour Index = jarak jaringan antar-simpul tanpa ruas snapping**
  (jarak centroid→simpul dan TES→simpul tidak ditambahkan), dipilih karena jumlah TAS cocok
  dengan draft. T_ideal memakai jarak Euclidean penuh centroid→TES, sehingga kedua besaran tidak
  sepenuhnya sebanding. — *DICATAT*
- **A6. Pemetaan level ke intensitas** (Rendah 0,25; Sedang 0,50; Tinggi 0,75) disimpulkan
  dengan mencocokkan rata-rata waktu tempuh draft. Intensitas 0,75 dan 1,0 menghasilkan grid
  terdampak dan ruas tertutup yang identik (semua kelas ≥ 1). — *DICATAT*
- **A7. Fitur klasterisasi memakai satu penanda `is_isolated`** (sesuai daftar 10 variabel),
  bukan lima penanda per kategori. Pilihan ini juga memperbaiki kecocokan level Tinggi dengan
  draft. — *DICATAT*

## B. Rumus SDWFCM dan SFCM (Langkah 2)

- **B1. Eksponen update keanggotaan SDWFCM salah.** `dt` sudah berupa jarak kuadrat, tetapi
  dipangkatkan `2/(m−1)` (efektif memangkatkan jarak dua kali). Diperbaiki menjadi
  u_ik = 1 / Σ_l (dt_ik/dt_il)^(1/(m−1)). Uji `tests/test_sdwfcm.py` memastikan untuk α = 0
  SDWFCM identik dengan FCM baku. — *DIPERBAIKI*
- **B2. Fungsi objektif SDWFCM tidak dijamin turun monoton untuk α > 0.** Suku spasial d_s
  bergantung pada u^m, sehingga aturan update keanggotaan (bentuk FCM) bukan peminimum eksak J.
  Pada data uji, J naik ~1·10⁻⁷ relatif di beberapa iterasi akhir (uji ditandai `xfail`).
  Implikasi: kriteria "J terkecil" pada multi-start tetap dapat dipakai sebagai kriteria pemilihan,
  tetapi klaim konvergensi monoton tidak boleh ditulis untuk α > 0. — *DICATAT*
- **B3. SFCM memakai rumus update yang salah secara struktur**: `1 / (Σ_l dt_ik/dt_il)^(2/(m−1))`
  (pangkat di luar penjumlahan, dan eksponen untuk jarak tak-kuadrat). Diperbaiki konsisten
  menjadi u_ik = 1 / Σ_l (dt_ik/dt_il)^(1/(m−1)) melalui fungsi yang sama dengan SDWFCM. — *DIPERBAIKI*
- **B4. Perhitungan ulang keanggotaan untuk metrik ketegasan partisi** juga memakai eksponen
  `2/(m−1)` pada jarak kuadrat; diselaraskan menjadi `1/(m−1)`. — *DIPERBAIKI*
- **B5. Bobot dampak ω hanya ada di pembilang d_s**:
  d_s,ik = Σ_j W_ij ω_j d_a,jk u_jk^m / Σ_j W_ij u_jk^m. Karena penyebut tidak memuat ω, d_s
  bukan rata-rata tertimbang yang ternormalisasi; tetangga terdampak memperbesar jarak spasial
  secara absolut. Apakah ini disengaja perlu dikonfirmasi. Bobot kini parameter
  `Cfg.sdwfcm_impact_weight = 2.0` dan dipakai sama di `fit()` dan `sdwfcm_objective()`. — *DICATAT*

## C. Implementasi dan data (ditemukan selama rekonstruksi)

- **C1. SKATER memakai fallback manual.** `spopt.region.Skater` (spopt 0.7.0) menolak argumen
  `min_region` (`TypeError`), sehingga perbandingan algoritma memakai fallback: MST pada graf
  ketetanggaan berbobot jarak atribut, lalu memotong K−1 sisi terpanjang. Pada data ini fallback
  menghasilkan satu klaster raksasa (Size Entropy ≈ 0,006). Silhouette SKATER yang tinggi (≈ 0,77)
  adalah artefak ketimpangan ukuran, bukan kualitas partisi. — *DICATAT*
- **C2. PESC sangat kecil walau sudah dalam km** (≈ 0,0004–0,007 km untuk K = 2–10). Nilainya tidak
  lagi dibulatkan (tidak ikut pembulatan 6 desimal), tetapi skala ini membuat PESC tidak informatif
  sebagai metrik pembanding. PESC tidak ikut skor komposit. — *DICATAT*
- **C3. Kode lama yang tidak dipakai masih ada.** `backend/engine.py` bagian 10, 11, 16, 17, 18
  (sudah diberi label "VERSI LAMA, TIDAK DIPAKAI") dan impor `backend/pseudo_safety.py` (dipakai
  jalur lama `simulate_*`). Kode ini tidak dihapus karena di luar lingkup instruksi. — *DICATAT*
- **C4. `is_isolated` biner dan jarang setelah Yeo-Johnson + standardisasi.** Nilai 1 hanya pada
  ≈ 0,5% grid di Baseline, sehingga setelah transformasi nilainya menjadi ekstrem dan berpotensi
  mendominasi satu komponen PCA. Tidak ada fitur yang terbuang oleh filter varians (10 fitur
  masuk, 5 komponen PCA, varians terjelaskan 85,2%). — *DICATAT*
- **C5. Kolom `id_grid` di GPKG ditimpa** dengan integer urut 0..N−1 saat pemuatan (peringatan di
  log). Penomoran grid di hasil adalah urutan baris GPKG, bukan ID asli berkas. — *DICATAT*
- **C6. Moran's I memakai 99 permutasi**, sehingga p minimum = 0,01. Semua algoritma memperoleh
  p = 0,01, jadi nilai p tidak membedakan algoritma. — *DICATAT*

## D. Pengamatan dari hasil final (untuk dibahas dengan pembimbing)

- **D1. Selisih skor K kecil.** K = 4 terpilih (skor 0,706) dengan runner-up K = 2 (0,689),
  selisih 0,017. DESC sangat tidak stabil antar-K (0,14 / 0,20 / 7,48 / 0,47 / 4,49 / … / 8,60)
  dan praktis menentukan urutan peringkat. Pemilihan K sebaiknya disajikan beserta tabel lengkap,
  bukan hanya pemenangnya.
- **D2. Tipologi baru di level Sedang dan Tinggi.** Dengan batas 2 × median jarak antarpusat
  Baseline (= 3,44), pada Sedang 2 dari 4 klaster, dan pada Tinggi 3 dari 4 klaster, tidak
  berpadanan dengan tipologi Baseline (jarak 9–20). Nomor klaster pada level itu tetap hasil
  pencocokan Hungarian, tetapi *maknanya* tidak boleh disamakan dengan klaster Baseline bernomor
  sama. Matriks transisi, SR, dan "klaster dominan" untuk level tersebut perlu dibaca dengan
  catatan ini.
- **D3. Grid Terputus sudah ada di Baseline** (168 grid), sedangkan grid terisolasi (opsi rute = 0)
  berjumlah 111. Perbedaan definisinya: Terputus = T_aktual sama dengan waktu penalti (termasuk
  grid yang gagal snapping ≤ 300 m), sedangkan terisolasi = tidak ada satu pun kategori TES yang
  terjangkau.
- **D4. REDCAP dan SKATER menghasilkan partisi sangat timpang** (Size Entropy 0,44 dan 0,006), dan
  proporsi tetangga berlabel sama ≈ 1 karena hampir semua grid berada di satu klaster.
  Perbandingan algoritma perlu membaca Size Entropy bersama metrik lain.

---

# Putaran 2 — revisi desain metode (branch `revisi-metode-v2`)

## P2-A. Kebersihan repo (Langkah 1)

- **P2-A1. Kode lama dihapus**: `backend/engine.py` bagian 10, 11, 16, 17, 18, `backend/pseudo_safety.py`,
  fungsi bantu `_resolve_cluster_profile_time_cols`, dan impor `kneed`. Pelacakan pemakaian:
  `backend/main.py` dan `frontend/` tidak memanggil satu pun fungsi tersebut, jadi dashboard tidak
  terdampak. — *SELESAI*
- **P2-A2. Sisa kode yatim.** Bagian 14 (`run_all_clustering`) dan 15 (`eval_one`, `evaluate_all`)
  di `engine.py` hanya dipanggil oleh pipeline lama yang sudah dihapus. Keduanya tidak termasuk daftar
  hapus di instruksi, jadi dibiarkan. Parameter `Cfg` milik kode lama (`psi_*`, `alr_*`,
  `elbow_*`, `threshold_n_classes`, `k_min_parsimony`) juga dibiarkan. — *DICATAT*
- **P2-A3. ID grid asli.** GPKG grid punya kolom `Id` (int, 22.673 nilai unik, tanpa null), jadi
  kolom ini dipakai sebagai `id_grid_asli` (disimpan sebagai teks) dan dibawa ke CSV grid, JSON
  dashboard, dan ekspor Excel. `id_grid` (0..N−1, urutan baris) tetap dipakai sebagai kunci JOIN
  dengan geometri statis dashboard. Bila `Id` tidak unik/lengkap, dipakai ID centroid
  `E{cx:.0f}_N{cy:.0f}`. — *SELESAI (menyelesaikan C5)*
- **P2-A4. Folder `scratch/` dihapus dari repo** dan diabaikan git. Dashboard membuatnya ulang
  otomatis (cache graf jalan dan `alamat_publik.txt`). Dua skrip diagnostik lama di
  `scratch/diagnostics/` ikut terhapus. — *SELESAI*

## P2-B. Waktu tempuh dan Detour Index (Langkah 3)

- **P2-B1. Waktu tempuh kini memuat ruas snapping**: (centroid → simpul jalan terdekat) + jarak
  jaringan + (simpul terdekat TES → titik TES), dibagi 80 m/menit. Batas snapping tetap 300 m.
  Implementasi: satu Dijkstra per kategori dari simpul sumber virtual yang terhubung ke simpul TES
  dengan bobot ruas snapping TES. T_pen = 3 × T_max Baseline dihitung ulang dari waktu baru.
  — *SELESAI (menyelesaikan A5)*
- **P2-B2. Kontradiksi instruksi yang diputuskan pengguna.** Pada Baseline, T_aktual ≥ jarak
  Euclidean murni berlaku untuk semua grid terjangkau. Namun 204 grid (0,9%) punya T_aktual < T_ideal
  karena batas minimum 50 m hanya dipasang pada T_ideal. **Keputusan pengguna:** batas 50 m dipasang
  pada kedua jarak, `T_aktual = max(jarak rute, 50 m)/80`. Akibatnya grid tersebut mendapat DI = 1.
  Test `tests/test_waktu_snapping.py` memeriksa T_aktual ≥ T_ideal pada data asli. — *SELESAI*

## P2-C. Desain gabungan dan pemilihan K (Langkah 4–7)

- **P2-C1. Langkah 5 (opsional) dijalankan.** Kelas bahaya banjir dikeluarkan dari fitur (9
  variabel). Keputusan diambil sebelum melihat hasil. Alasannya: setelah grid Tergenang dikeluarkan,
  kelas bahaya grid yang tersisa hampir hanya menandai level (pada Tinggi semua grid non-Tergenang
  berkelas 0). Bila pembimbing ingin mempertahankan 10 variabel, cukup kembalikan `SKENARIO` ke
  `feature_columns` lalu jalankan ulang. — *DIPUTUSKAN, perlu dikonfirmasi*
- **P2-C2. σ kernel Gaussian dihitung per blok level** (median jarak 8 tetangga di dalam level
  tersebut), karena W dibangun hanya di antara grid non-Tergenang pada level yang sama. Instruksi
  tidak menyebut apakah σ global atau per level. Nilai σ per level tercatat di hasil. — *DICATAT*
- **P2-C3. B = 10 dipertahankan.** Estimasi waktu dibuat sebelum run dan hanya dari pengukuran waktu:
  satu fit data penuh ≈ 3,6·K detik, satu fit subsampel ≈ 2,9·K detik. Total pemilihan K ≈
  10·3,6·54 + 30·2,9·54 ≈ 6.600 detik, sehingga satu run ≈ 2 jam (< 3 jam). — *DICATAT*
- **P2-C4. Rincian pelaksanaan subsampel yang tidak ditentukan instruksi** (ditetapkan sebelum
  melihat hasil): seed pemilihan subsampel ke-b = 20240 + b; tiga inisialisasi subsampel memakai seed
  42–44; W blok-diagonal dihitung ulang pada tiap subsampel; praproses TIDAK di-fit ulang (fit sekali
  pada data gabungan penuh); solusi data penuh pembanding = run dengan J terkecil di antara seed
  42–51 (sama dengan model final). — *DICATAT*
- **P2-C5. Simulasi blokir jalan di dashboard** kini menghitung keanggotaan terhadap pusat klaster
  final yang tetap (tidak di-fit ulang), karena model gabungan tidak dapat di-fit ulang untuk satu
  level saja tanpa mengubah makna nomor klaster. Ini hanya fitur dashboard, bukan hasil skripsi. — *DICATAT*

## P2-D. Perbandingan algoritma dan metrik (Langkah 8–9)

- **P2-D1. SKATER tetap gagal walau argumen sudah benar (`floor`).** Signature di spopt 0.7.0:
  `Skater(gdf, w, attrs_name, n_clusters=5, floor=-inf, trace=False, islands='increase', ...)`.
  Penyebab kegagalan: spopt menghitung kernel ketidakmiripan padat N × N, mengalikannya dengan W,
  lalu **membuang sisi berbobot 0**, yaitu pasangan tetangga dengan fitur identik. Graf pun terpecah
  menjadi "pulau" kecil, dan spopt menolak bila ada pulau yang lebih kecil dari `floor` (galat
  "Islands must be larger than the quorum"). Sesuai instruksi, fallback manual dihapus, SKATER
  dilaporkan gagal dan tidak layak dibandingkan, dan tidak diganti metode lain. Solusi teknis yang
  mungkin (tidak dilakukan): menambahkan konstanta kecil pada ketidakmiripan, atau menghapus pulau
  sebelum SKATER. — *DILAPORKAN, perlu diputuskan*
- **P2-D2. SFCM tetap memakai m = 2,0** (parameter bawaan `Cfg.sfcm_m`), sedangkan FCM dan SDWFCM
  memakai m = 1,7. Instruksi menyeragamkan praproses, K, inisialisasi, dan penomoran, tetapi tidak
  menyebut m. — *DICATAT*
- **P2-D3. Kriteria pemilihan inisialisasi SFCM** = J_SFCM = Σ u^m·d_t pada keanggotaan akhir.
  SFCM sebelumnya tidak punya fungsi objektif; kriteria ini ditambahkan agar "10 inisialisasi,
  J terkecil" berlaku seragam. Loop per grid SFCM divektorisasi (matematika identik, diuji) agar
  10 inisialisasi layak dijalankan. — *DICATAT*
- **P2-D4. Silhouette pada perbandingan algoritma dihitung penuh** (22.673 grid Baseline), sedangkan
  pada pemilihan K memakai sampel 10.000 (data gabungan ± 72 ribu baris). — *DICATAT*

## P2-E. Status temuan lama setelah putaran 2

| Temuan | Status | Keterangan |
|---|---|---|
| A1 (DESC blok queen) | **Selesai** | Blok DESC/PESC kini rook, sama dengan W Moran (Langkah 9) |
| A4 (Dunn satu sampel) | **Selesai** | 5 sampel (seed 42–46), rerata dan sd (Langkah 9) |
| A5 (T_aktual tanpa ruas snapping) | **Selesai** | Ruas snapping masuk di waktu tempuh dan T_aktual (Langkah 3; P2-B) |
| A6 (level ← intensitas hasil kalibrasi) | **Selesai** | Level didefinisikan dengan kelas ditutup; ekuivalensi diuji (Langkah 2) |
| C1 (fallback SKATER) | **Selesai, masalah baru** | Fallback dihapus; spopt tetap gagal (P2-D1) |
| C3 (kode lama) | **Selesai** | Bagian lama dihapus; sisa yatim dicatat di P2-A2 |
| C5 (id_grid ditimpa) | **Selesai** | `id_grid_asli` dari kolom `Id` (P2-A3) |
| D1 (selisih skor K tipis) | **Diganti** | Aturan K berbasis stabilitas; skor komposit hanya sensitivitas (Langkah 7) |
| D2 (tipologi baru antarlevel) | **Tidak relevan lagi** | Satu model gabungan untuk semua level; Hungarian dihapus (Langkah 6) |
| B5 (ω hanya di pembilang d_s) | **Tidak berpengaruh** | ω = 1,0 (nonaktif) pada desain gabungan |

## P2-F. Pengamatan dari hasil v2 (untuk dibahas dengan pembimbing)

- **P2-F1. K = 2 terpilih menurut aturan, tetapi K = 3 praktis setara.** Rerata ARI subsampel: K = 2
  0,964 ± 0,006; K = 3 0,963 ± 0,003 (selisih 0,001, dalam toleransi 0,01), sehingga aturan memilih
  K terkecil. K = 3 punya ARI inisialisasi 1,000 (K = 2: 0,999), Silhouette dan ketegasan partisi
  lebih tinggi, dan dipilih oleh skor komposit lama baik dengan maupun tanpa DESC. Dengan K = 2,
  tipologi hanya membedakan "akses baik" (K0, waktu minimum rata-rata 4,9 menit) dan "akses kritis"
  (K1, 41,8 menit). Aturan tidak diubah. — *PERLU DIPUTUSKAN*
- **P2-F2. Stabilitas K = 5, 6, 7, 9 rendah dan bervariasi besar** (sd ARI subsampel 0,15–0,22;
  ARI inisialisasi K = 6, 7, 9, 10 ≈ 0,72–0,79), sedangkan K = 8 dan K = 10 kembali stabil secara
  subsampel (≈ 0,94). — *DICATAT*
- **P2-F3. PESC meledak pada beberapa K** (mis. K = 5: 5.974; K = 9: 23.996; K = 10: 31.110),
  karena jarak atribut antarpusat blok mendekati 0 membuat penyebut sangat kecil. PESC tidak
  informatif sebagai pembanding (melanjutkan C2). DESC dengan blok rook juga jauh lebih besar daripada
  v1 queen (24–44 untuk K ≥ 3). — *DICATAT*
- **P2-F4. Semua TAS juga lolos ambang absolut DI ≥ 2** (100% di keempat level), karena P75 DI
  pada grid terjangkau selalu ≥ 2. Uji sensitivitas menghasilkan lebih banyak TAS (seluruh grid dekat
  dengan DI ≥ 2), bukan lebih sedikit. — *DICATAT*
- **P2-F5. Kebetulan angka di level Sedang:** jumlah grid K1 (7.845) sama dengan jumlah grid
  Tergenang (7.845). Sudah diverifikasi dari dua berkas independen (label data gabungan dan state
  grid) dan bukan galat. — *DICATAT*
- **P2-F6. Transisi Baseline → Tinggi berubah drastis**: 35,5% grid masuk Tergenang, dan ARI pada
  grid yang tetap non-Tergenang hanya 0,012 (stability rate 59,6%). Transisi dominan pada tiga dari
  empat pasangan adalah K0 → Tergenang. Transisi Sedang → Tinggi yang dominan adalah K0 → K1 (2.092
  grid), karena hanya 196 grid kelas 1 yang menjadi Tergenang. — *DICATAT*
- **P2-F7. REDCAP degeneratif** (klaster terbesar 98,2%) dan **SKATER gagal** (P2-D1), sehingga
  perbandingan yang layak hanya FCM, SFCM, dan SDWFCM. Di antara ketiganya, Silhouette/CH/DB hampir
  sama (0,317–0,325), sedangkan SDWFCM unggul pada Moran's I (0,832) dan proporsi tetangga berlabel
  sama (0,917). — *DICATAT*
- **P2-F8. σ kernel Gaussian = 141,42 m pada keempat level** (median jarak 8 tetangga pada grid
  teratur 100 m), jadi pilihan σ per level vs global (P2-C2) tidak berpengaruh. — *DICATAT*
- **P2-F9. Waktu komputasi.** Log mencatat total 15.086 detik, tetapi termasuk jeda ± 8.890 detik saat
  komputer sleep (13:32–16:00, kedua run berhenti bersamaan pada K = 4). Waktu efektif ± 6.200 detik
  (± 1,7 jam), sesuai estimasi P2-C3. — *DICATAT*

---

# Putaran 3 (branch `revisi-v3`)

- **P3-1. Kelas bahaya ruas jalan dan TES berasal dari sumber berbeda dengan kelas grid.** Rincian,
  besaran dampak, dan opsi ada di `docs/DIAGNOSTIK_JALAN_GRID.md`. Kesesuaian kelas ruas vs grid yang
  dilalui hanya 61% (panjang). Level Rendah praktis tidak menutup jalan di area penelitian (3,6 km).
  Sebanyak 161 km ruas tertutup di Level Tinggi melintasi grid kelas 0. Setelah raster tersedia,
  kesimpulan dikoreksi (P3-2). — *DIPUTUSKAN: opsi 3 (turunkan ulang dari raster)*
- **P3-2. Raster sumber menunjukkan bahwa kelas GRID-lah yang tidak berasal dari raster** (kecocokan
  64–65%), sedangkan ruas (98,7%) dan TES (100%) berasal dari raster. Keputusan peneliti: semua kelas
  diturunkan dari `data/Kulonprogo_Banjir.tif` (grid mayoritas, ruas maksimum, TES titik; nodata = 0).
  Grid Tergenang berubah menjadi Rendah 39 / Sedang 3.375 / Tinggi 7.175 (lama 2.531 / 7.845 / 8.041).
  Level Rendah kini hampir tanpa grid Tergenang. — *SELESAI (kode); dampak dibahas di laporan*
- **P3-3. Aturan seri mayoritas dan grid tanpa pusat piksel.** Seri → kelas terendah (sesuai angka
  yang diperlihatkan saat keputusan); 65 grid tepi tanpa pusat piksel memakai piksel di centroid.
  Keduanya ditetapkan sebelum melihat hasil model. — *DICATAT*
- **P3-4. Stabilitas K dihitung ulang** (keputusan peneliti), berbeda dengan instruksi awal Putaran 3,
  karena data gabungan berubah. Keluaran lengkap tetap untuk K = 2 dan K = 3. — *DIPUTUSKAN*
- **P3-5. Langkah 8 selesai.** Kode yatim (`run_all_clustering`, `_run`, `eval_one`, `evaluate_all`,
  `_size_entropy`) dan parameter `Cfg` yang tidak dirujuk dihapus setelah diverifikasi dengan grep,
  pytest, dan smoke test. `k_range` dan `sdwfcm_sigma` ikut dihapus karena hanya dirujuk kode yatim
  (K_RANGE di thesis.py yang berlaku). — *SELESAI*
- **P3-6. Kelas bahaya ruas dengan aturan maksimum** menaikkan kelas 2.477 ruas dibanding atribut
  lama. Atribut lama tampaknya diambil dari satu titik per segmen. — *DICATAT*
- **P3-7. `pengaturan_hasil.json`** menyimpan K utama (bawaan 3) untuk export dan dashboard. Berkas ini
  bukan bagian dari hasil terkunci; mengubahnya tidak mengubah analisis, hanya susunan tabel utama
  vs sensitivitas. — *DICATAT*

## Status temuan Putaran 2 setelah Putaran 3

| Temuan | Status | Keterangan |
|---|---|---|
| P2-A2 (kode yatim di engine) | **Selesai** | Dihapus di Langkah 8 (P3-5) |
| P2-D2 (m SFCM berbeda) | **Selesai** | SFCM memakai m = 1,7 yang sama (`sfcm_m` dihapus) |
| P2-F1 (K = 2 vs K = 3 setara) | **Ditangani** | Stabilitas dihitung ulang pada data v3; keluaran lengkap untuk K = 2 dan 3; model utama diputuskan peneliti (METODOLOGI §9) |
| P2-F3 (PESC meledak) | **Ditangani** | PESC, DESC, I-Index, Dunn, dan komposit dipindah ke tabel lampiran L01 |
| P2-F4 (semua TAS lolos DI ≥ 2) | **Selesai** | Aturan utama kini absolut (DI ≥ 2 dan T_ideal ≤ 5 menit); persentil menjadi sensitivitas |
| P2-D1 (SKATER gagal) | Tetap | Dilaporkan gagal untuk kedua K, tanpa fallback |

## P3-H. Pengamatan dari hasil v3 (untuk dibahas dengan pembimbing)

- **P3-8. Pada data v3, K = 3 TIDAK lagi setara secara stabilitas dengan K = 2.** Rerata ARI subsampel:
  K = 2 0,957 ± 0,004; K = 4 0,949 ± 0,003 (setara, selisih 0,008); K = 3 0,940 ± 0,006 (selisih 0,017 >
  0,01). Aturan stabilitas tetap memilih K = 2. Premis "K = 2 dan K = 3 tidak terbedakan" hanya
  berlaku untuk data v2. Silhouette K = 3 (0,156) juga lebih rendah daripada K = 2 (0,243) dan K = 4
  (0,203). — *PERLU DIPUTUSKAN (K utama)*
- **P3-9. Label interpretasi kurang membedakan.** Dengan aturan median, kedua klaster K = 2 berlabel
  "Akses Baik" (median waktu minimum 3,7 dan 8,9 menit). Pada K = 3, K0 dan K1 "Akses Baik" (3,3 dan
  5,8 menit), sedangkan K2 "Akses Sedang" (11,9 menit). Rerata dan median sangat berbeda pada klaster
  terburuk (K = 3 K2: rerata 36,6 vs median 11,9), karena 6% barisnya bernilai penalti. Ambang label
  ditetapkan sebelum hasil dan tidak diubah. — *DICATAT*
- **P3-10. Aturan TAS absolut menghasilkan jauh lebih banyak TAS**: ±25% grid non-Tergenang (Baseline
  5.758 vs aturan persentil 1.842). Semua TAS aturan persentil juga termasuk TAS aturan absolut. Median
  T_ideal TAS 2,3 menit (± 190 m) vs T_aktual 7,0 menit. DI ≥ 2 mudah tercapai pada jarak pendek
  karena ruas snapping dan pola jaringan lokal. Ambang ini mungkin terlalu longgar untuk disebut "semu".
  — *PERLU DIPUTUSKAN*
- **P3-11. Level Rendah hampir identik dengan Baseline** (39 grid Tergenang, 710 ruas ditutup, TES valid
  tetap 1.434; SR K = 2 99,8%, ARI 0,991), karena raster hanya memuat 8,7 km² kelas 3 dan hanya 39 grid
  yang mayoritas pikselnya kelas 3. — *DICATAT*
- **P3-12. TAS per kategori TES terdekat** didominasi Tempat Ibadah (Baseline 3.403 dari 5.758 = 59%)
  dan Pendidikan (31%), sesuai sebaran TES terbanyak. — *DICATAT*
- **P3-13. Perbandingan algoritma v3.** Untuk kedua K, SDWFCM punya Moran's I dan proporsi tetangga
  berlabel sama tertinggi di antara algoritma fuzzy. Pada K = 3, SDWFCM juga unggul Silhouette (0,209)
  dan DB (1,498). Pada K = 2, FCM sedikit lebih tinggi pada Silhouette/CH (0,303 vs 0,296). REDCAP
  degeneratif (95,8% dan 98,2%), dan SKATER gagal untuk kedua K. — *DICATAT*
- **P3-14. Waktu komputasi.** Dua run bersamaan tanpa jeda sleep (dicegah `SetThreadExecutionState`
  selama run). Run A 7.743 detik (pemilihan K 7.505 detik), run B 7.800 detik. Fingerprint identik.
  — *DICATAT*

---

# Putaran 4 (branch `revisi-v4`)

- **P4-1. Placeholder ambang T_aktual di instruksi.** Instruksi awal memuat "[X]" dan "[isi rujukan]".
  Pengguna menetapkan X = 30 menit (Li dkk., 2026; Park dkk., 2020) sebelum hasil v4 terlihat. Rujukan
  dan status verifikasinya ada di `docs/RUJUKAN_PARAMETER.md`. — *DIPUTUSKAN pengguna*
- **P4-2. Pemilihan K tidak dijalankan ulang.** Pipeline memakai tabel stabilitas v3
  (`data/locked/arsip_v3/thesis_results.json`) setelah memverifikasi bahwa data gabungan identik
  (baris, level, skor PCA; toleransi 2·10⁻⁶ karena pembulatan 6 desimal di berkas v3). Label K = 2 dan
  K = 3 diverifikasi identik dengan v3 (`verifikasi_v3`). — *SELESAI*
- **P4-3. Satu konstanta batas waktu evakuasi** (`EVAC_TIME_MIN = 30`, `EVAC_TIME_SENS = (20, 40)`)
  dipakai oleh aturan TAS, kategori akses "Jauh", dan ambang isolasi REDCAP. Test `tokenize`
  memastikan tidak ada literal 30 lain di `backend/` dan `scripts/`. Kelas waktu tempuh di legenda
  dashboard (≤ 5, 5–10, …, 15–30, 30–60 menit) adalah penyajian warna frontend dan tidak diikat ke
  konstanta ini. — *SELESAI*
- **P4-4. Sensitivitas 15 menit** tidak pernah ada di kode, jadi tidak ada yang diganti; sensitivitas
  20 dan 40 menit ditambahkan. — *DICATAT*
- **P4-5. Kecepatan 80 m/menit ≈ 4,8 km/jam**, sedikit di bawah asumsi 5 km/jam pada Li dkk. (2026).
  Parameter tidak diubah (di luar instruksi); dicatat untuk verifikasi peneliti. — *DICATAT*
- **P4-6. Label tipologi diganti label peringkat** (penyajian, bukan perubahan model), menjawab P3-9.
  — *SELESAI*

## P4-H. Pengamatan dari hasil v4 (untuk dibahas dengan pembimbing)

- **P4-7. K = 4 memisahkan grid Terputus/terisolasi.** Tipologi 4 (terburuk) berisi 1.422 baris (1,8%).
  Sebanyak 96,3% barisnya bernilai penalti (Terputus), 98,8% berwaktu minimum > 30 menit, dan proporsi
  terisolasi 0,963. Tipologi 1–3 hampir tanpa penalti (≤ 0,07%) dan membagi grid terhubung menurut
  waktu tempuh: median 3,4 / 4,3 / 9,9 menit, P90 6,6 / 6,9 / 18,2 menit. — *DICATAT*
- **P4-8. Aturan TAS utama v4 sangat ketat.** TAS Baseline/Rendah/Sedang/Tinggi = 62 / 70 / 77 / 44
  (0,27–0,40% grid non-Tergenang), dibanding 5.758 pada aturan absolut v3 dan 1.842 pada aturan
  persentil. Hanya 36–55% TAS utama yang tetap TAS pada ambang 40 menit, jadi jumlahnya peka terhadap
  ambang. Median T_aktual TAS 35–43 menit. — *PERLU DIBAHAS*
- **P4-9. TAS baru akibat banjir kecil**: Rendah 8, Sedang 54, Tinggi 27, semuanya dari Non-TAS
  Baseline. TAS hilang Sedang 39 (31 jadi Tergenang, 7 jadi Terputus) dan Tinggi 45 (35 jadi Tergenang,
  8 jadi Terputus). — *DICATAT*
- **P4-10. Dua definisi "Terputus" berbeda jumlahnya.** Kategori akses Terputus (waktu minimum =
  penalti, tidak mencapai TES mana pun) di Baseline = 111. Status TAS Terputus (T_aktual ke TES
  Euclidean terdekat = penalti) = 168. Selisihnya adalah grid yang tidak dapat mencapai TES terdekat
  secara garis lurus, tetapi masih mencapai TES lain. — *DICATAT*
- **P4-11. REDCAP K = 4 tidak ditandai degeneratif** (klaster terbesar 89,3%, tepat di bawah batas
  90%), tetapi Silhouette 0,002 dan CH 256. Batas degeneratif ditetapkan sebelumnya dan tidak diubah.
  — *DICATAT*
- **P4-12. Kategori akses (30 menit).** Porsi Terjangkau: Baseline 98,6%, Rendah 98,2%, Sedang 82,6%,
  Tinggi 64,1%. Grid "Jauh" hanya 0,3–1,4%, dan "Terputus" 0,5–2,9%. Penurunan akses terutama
  disebabkan grid Tergenang (14,9% dan 31,6%), bukan waktu tempuh > 30 menit. — *DICATAT*
- **P4-13. Waktu komputasi.** Pemilihan K tidak dijalankan ulang, sehingga satu run ± 8,6 menit (518 dan
  507 detik). Kedua run tanpa jeda (sleep dicegah) dan fingerprint identik. — *DICATAT*

---

# Putaran 5 (branch `revisi-v5`, hasil final)

Model, K, data, dan semua ambang tidak diubah; putaran ini hanya penyajian, validasi, dan finalisasi.

- **P5-1. K utama = 4** (`pengaturan_hasil.json`), dipilih peneliti setelah hasil v3/v4 terlihat dari
  himpunan K yang setara secara stabilitas {2, 4}, karena memisahkan tipologi Terputus (P4-7). K = 2 dan
  K = 3 menjadi sensitivitas. Ditulis di METODOLOGI §9 (e). — *SELESAI*
- **P5-2. Status TAS 2 berganti nama menjadi "TES terdekat tidak terjangkau"** di keluaran, dashboard,
  dan dokumentasi (menyelesaikan P4-10). Kunci JSON ikut berganti (`jumlah_tes_terdekat_tidak_terjangkau`,
  `tas_hilang_jadi_tes_terdekat_tidak_terjangkau`), sehingga fingerprint v5 berbeda dengan v4, walaupun
  semua angka sama. Perbedaan kedua definisi dijelaskan di METODOLOGI §11b. — *SELESAI*
- **P5-3. Catatan "nyaris degeneratif"** pada tabel algoritma memakai aturan penyajian klaster
  terbesar ≥ 85% (batas degeneratif tetap 90%). Aturan ini hanya berlaku untuk REDCAP K = 4 (89,3%).
  — *SELESAI (menjawab P4-11)*
- **P5-4. Lembar validasi TAS** (`output_bab4/validasi/validasi_TAS.xlsx` + peta per TAS) dibuat oleh
  `scripts/lembar_validasi_TAS.py`. Skrip ini menghitung ulang rute jaringan dengan aturan yang sama dan
  mencocokkan T_aktual dengan nilai terkunci (kolom "Cek T_aktual"). Rekap dibuat oleh
  `scripts/rekap_validasi_TAS.py` setelah lembar diisi peneliti (belum dijalankan). — *MENUNGGU PENGISIAN*
- **P5-5. Referensi draft lama di kode**: tidak ada (diperiksa dengan grep di backend/, scripts/,
  frontend/, tests/). `docs/angka_draft_lama.json` tetap sebagai arsip dokumentasi. — *SELESAI*

---

# Diagnostik topologi jaringan (branch `diagnostik-topologi`; hasil v5 tidak diubah)

**Definisi dan toleransi (ditetapkan sebelum melihat hasil):**

- Graf dibangun persis seperti `build_road_graph`: simpul = ujung segmen dibulatkan 0,01 m; sisi =
  segmen (semua segmen jalan GPKG berupa garis 2 titik).
- **Segmen khusus** = `bridge = T` atau `tunnel = T` atau `layer ≠ 0`. Perpotongan atau sambungan yang
  melibatkan segmen khusus dianggap wajar tidak tersambung, sehingga tidak dihitung sebagai artefak dan
  tidak disambungkan saat perapian.
- **Ujung buntu** = simpul berderajat 1.
- **Near-miss** pada toleransi d ∈ {0,5; 1; 2; 5} m: ujung buntu u yang punya titik pada sisi lain e
  berjarak ≤ d dengan tiga syarat: (i) e tidak bersisian dengan u; (ii) tidak ada ujung e yang dapat
  dicapai dari u dalam jarak jaringan ≤ 20 m (agar sisi tetangga di jalan yang sama tidak ikut
  terhitung); (iii) u dan e bukan segmen khusus.
- **Perpotongan tanpa simpul** = dua sisi yang berpotongan geometris di satu titik tanpa berbagi ujung.
  Dilaporkan terpisah: yang melibatkan segmen khusus vs yang tidak.
- **Per TAS**: diklasifikasikan "kemungkinan artefak topologi" bila ada near-miss ≤ 2 m atau
  perpotongan tanpa simpul (non-khusus) dalam radius 100 m dari garis lurus grid–TES terdekat. Selain
  itu diklasifikasikan "tidak terdeteksi artefak". Komponen terhubung simpul grid dan simpul TES
  dilaporkan pada graf Baseline.
- **Jaringan dirapikan** (toleransi utama 1 m, sensitivitas 2 m):
  - (a) noding: sisi non-khusus yang berpotongan dipecah di titik potong dan disambungkan;
  - (b) setiap near-miss pada toleransi tersebut disambungkan ke titik terdekat pada sisi sasaran
    (sisi dipecah bila titiknya bukan ujung), dengan panjang sambungan = jarak.
  - Sisi hasil pecahan mewarisi segmen sumbernya. Pada level banjir, sisi dan sambungan yang segmen
    sumbernya ditutup ikut dihapus.
- **Perhitungan ulang** per level: waktu tempuh, kategori akses (20/30/40 menit), dan TAS aturan utama,
  dengan T_pen v5 (403,87 menit) dan aturan yang sama. Klasterisasi tidak di-fit ulang. "Tipologi 4 v5
  menjadi terjangkau" = baris data gabungan K = 4 berlabel 3 yang waktu minimumnya < T_pen pada
  jaringan dirapikan.

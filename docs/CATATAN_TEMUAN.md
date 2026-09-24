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

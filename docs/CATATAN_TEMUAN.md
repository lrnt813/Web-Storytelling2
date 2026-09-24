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

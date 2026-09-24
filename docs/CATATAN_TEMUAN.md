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

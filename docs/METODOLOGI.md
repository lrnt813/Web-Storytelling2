# Metodologi — sebagaimana diimplementasikan

Dokumen ini menjelaskan pipeline analisis **persis seperti kode** di `backend/engine.py`,
`backend/thesis.py`, dan `scripts/thesis_analysis.py`. Nilai parameter yang dipakai pada run
final tercatat di `data/locked/LOCK.json`. Hal yang masih perlu diputuskan tercatat di
`docs/CATATAN_TEMUAN.md`.

## 1. Unit analisis dan data

- Unit analisis: grid 100 m × 100 m (\(N = 22.673\)), CRS EPSG:32749. Titik asal setiap grid
  adalah centroid-nya.
- Atribut grid: kepadatan jaringan jalan `Road_Density_mean` dan kelas bahaya banjir
  \(h_i \in \{0,1,2,3\}\).
- Jaringan jalan: 162.608 segmen, masing-masing berkelas bahaya \(c \in \{0,1,2,3\}\).
- TES: lima kategori (pendidikan, kesehatan, pemerintahan, ibadah, GOR/gedung serbaguna),
  masing-masing titik berkelas bahaya.

## 2. Simulasi intensitas banjir

Empat level dengan intensitas \(I\): Baseline 0; Rendah 0,25; Sedang 0,50; Tinggi 0,75.

**Grid terdampak.** Peluang dampak dinormalisasi dari kelas bahaya:
\[
p_i = \frac{h_i - \min_j h_j}{\max_j h_j - \min_j h_j}, \qquad
\text{terdampak}_i \iff I > 0 \;\wedge\; p_i \ge 1 - I \;\wedge\; p_i > 0 .
\]

**Ruas jalan ditutup.** Dengan \(\eta(c)\) = {0: 0; 1: 0,33; 2: 0,67; 3: 1,00} dan \(\tau = 0{,}20\):
\[
\text{ditutup}_e \iff \eta(c_e)\cdot I \ge \tau .
\]

Kelas bahaya yang terkena (diturunkan dari kedua aturan di atas dan diverifikasi dari data):

| Level | \(I\) | Grid terdampak | Ruas ditutup |
|---|---:|---|---|
| Baseline | 0,00 | – | – |
| Rendah | 0,25 | kelas 3 | kelas 3 |
| Sedang | 0,50 | kelas ≥ 2 | kelas ≥ 2 |
| Tinggi | 0,75 | kelas ≥ 1 | kelas ≥ 1 |

## 3. Filter TES

TES valid bila kelas bahayanya \(< 2\). Pada level dengan \(I > 0\), TES berkelas \(< 2\) yang
berada dalam radius 50 m dari grid terdampak dinaikkan kelasnya menjadi 3, sehingga tidak valid.

## 4. Waktu tempuh ke TES, snapping, dan penalti

1. Graf jaringan jalan dibentuk dari ruas yang tidak ditutup. Simpul = ujung segmen (dibulatkan
   0,01 m); bobot sisi = panjang segmen \(\ell_e\) (m).
2. Centroid grid dan titik TES di-*snap* ke simpul jalan terdekat bila jaraknya \(\le 300\) m;
   jika tidak, dianggap tidak terhubung.
3. Untuk setiap kategori \(q\), jarak jaringan \(D_{iq}\) dihitung dengan Dijkstra multi-sumber
   (sumber = semua TES valid kategori \(q\)). Kecepatan berjalan \(v = 80\) m/menit:
\[
t_{iq} = \begin{cases} D_{iq}/v & \text{bila terjangkau} \\ T_{\text{pen}} & \text{bila tidak} \end{cases},
\qquad T_{\text{pen}} = 3\,T_{\max},
\]
   dengan \(T_{\max}\) = waktu tempuh **maksimum** yang valid (terjangkau, \(>0\)) di seluruh
   kategori pada Baseline. \(T_{\text{pen}}\) dikunci untuk semua level.
4. Variabel turunan:
\[
t_i^{\min} = \min_q t_{iq}, \qquad
\text{opsi}_i = \sum_q \mathbf{1}[t_{iq} < T_{\text{pen}}], \qquad
\text{isolated}_i = \mathbf{1}[\text{opsi}_i = 0].
\]

## 5. Pra-pemrosesan (di-fit pada Baseline)

Variabel masukan (10): `Road_Density_mean`, \(t_{i,q}\) untuk 5 kategori, \(t_i^{\min}\),
`jumlah_opsi_rute`, `is_isolated`, kelas banjir \(h_i\). Semua parameter diestimasi **sekali
pada Baseline** lalu diterapkan tanpa fit ulang ke Rendah, Sedang, dan Tinggi:

1. Nilai hilang diisi median Baseline.
2. Capping Tukey hanya untuk `Road_Density_mean`: \(x \mapsto \min(\max(x, Q_1 - 3\,\mathrm{IQR}), Q_3 + 3\,\mathrm{IQR})\).
   Waktu tempuh, opsi rute, penanda isolasi, dan kelas banjir tidak di-capping.
3. Seleksi fitur: pertahankan variabel dengan varians Baseline \(> 10^{-3}\).
4. Yeo–Johnson per variabel (\(\lambda\) diestimasi dengan *maximum likelihood*), lalu
   standardisasi \(z = (y - \bar y)/s_y\).
5. RobustScaler: \(z' = (z - \mathrm{median}(z)) / \mathrm{IQR}(z)\).
6. PCA dengan jumlah komponen terkecil yang varians kumulatifnya \(\ge 80\%\).

Hasil: matriks \(X\) (satu baris per grid) dalam **ruang PCA bersama** untuk keempat level.

## 6. Matriks bobot spasial SDWFCM (KNN-Gaussian)

Untuk tiap grid \(i\), \(\mathcal N_i\) = 8 tetangga terdekat (jarak centroid \(r_{ij}\)).
\[
\sigma = \mathrm{median}\{ r_{ij} : j \in \mathcal N_i,\ \forall i\}, \qquad
W_{ij} = \frac{\exp\!\left(-r_{ij}^2 / 2\sigma^2\right)}{\sum_{l \in \mathcal N_i} \exp\!\left(-r_{il}^2 / 2\sigma^2\right)} \;\; (j \in \mathcal N_i).
\]

Matriks ini **berbeda** dari matriks ketetanggaan rook (§12) yang dipakai algoritma pembanding
dan Moran's I.

## 7. SDWFCM

Parameter: \(m = 1{,}7\), \(\alpha = 0{,}5\), KNN = 8, bobot dampak \(\omega = 2{,}0\)
(`sdwfcm_impact_weight`), toleransi \(10^{-4}\), maksimum 150 iterasi.

Bobot dampak tetangga: \(\omega_j = \omega\) bila grid \(j\) terdampak, selain itu 1.

Untuk keanggotaan \(U = [u_{ik}]\):
\[
v_k = \frac{\sum_i u_{ik}^m x_i}{\sum_i u_{ik}^m}, \qquad
d^{a}_{ik} = \lVert x_i - v_k \rVert^2 ,
\]
\[
d^{s}_{ik} = \frac{\sum_j W_{ij}\,\omega_j\, d^{a}_{jk}\, u_{jk}^m}{\sum_j W_{ij}\, u_{jk}^m}, \qquad
d^{t}_{ik} = (1-\alpha)\, d^{a}_{ik} + \alpha\, d^{s}_{ik} .
\]

(\(\omega_j\) hanya ada di pembilang; lihat CATATAN_TEMUAN B5.)

Update keanggotaan (\(d^t\) sudah berupa jarak kuadrat):
\[
u_{ik} = \left[ \sum_{l=1}^{K} \left( \frac{d^{t}_{ik}}{d^{t}_{il}} \right)^{1/(m-1)} \right]^{-1}.
\]

Iterasi: \(U^{(0)} \sim \mathrm{Dirichlet}(1,\dots,1)\) per grid; ulangi \(d^t(U^{(r)}) \to U^{(r+1)}\)
sampai \(\lVert U^{(r+1)} - U^{(r)} \rVert_F < 10^{-4}\). Label keras \(= \arg\max_k u_{ik}\).

Fungsi objektif (dihitung dengan fungsi jarak yang sama):
\[
J(U) = \sum_{i=1}^{N} \sum_{k=1}^{K} u_{ik}^m\, d^{t}_{ik}(U).
\]
Untuk \(\alpha = 0\), SDWFCM identik dengan FCM baku (diuji di `tests/test_sdwfcm.py`). Untuk
\(\alpha > 0\), \(J\) tidak dijamin turun monoton (CATATAN_TEMUAN B2).

**Multi-start.** SDWFCM dijalankan dengan 10 seed (42, 43, …, 51) dan dipilih solusi dengan
\(J\) terkecil.

## 8. Pemilihan K (pada Baseline)

Untuk \(K = 2, \dots, 10\): SDWFCM multi-start (10 seed), lalu dihitung:

- **I-Index** (\(p = 2\)), dengan \(c_k\) = pusat fuzzy (CATATAN A2):
  \(I(K) = \left(\frac1K \cdot \frac{E_1}{E_K} \cdot D_K\right)^2\),
  \(E_1 = \sum_i \lVert x_i - \bar x\rVert\), \(E_K = \sum_k \sum_{i \in C_k} \lVert x_i - c_k\rVert\),
  \(D_K = \max_{k,l} \lVert c_k - c_l\rVert\).
- **Dunn** titik-ke-titik pada sampel 2.000 grid (seed 42; CATATAN A4):
  \(\min_{i,j \text{ beda klaster}} \lVert x_i - x_j\rVert \,/\, \max_{i,j \text{ sama klaster}} \lVert x_i - x_j\rVert\).
- **DESC**: blok = komponen terhubung grid berlabel sama pada ketetanggaan *queen* (CATATAN A1);
  \(\mathrm{DESC} = \sum_{b,\ |b|\ge 2} V_b^2 / \delta_b^2\), dengan \(V_b\) = ukuran blok / ukuran
  klasternya dan \(\delta_b\) = rata-rata jarak atribut anggota ke pusat blok.
- **PESC**: \(\sum_k \sum_{b<b'} V_b V_{b'} / (S_{bb'}\, \Delta_{bb'}\, B_k)\), dengan \(S\) =
  jarak spasial antarpusat blok (**km**), \(\Delta\) = jarak atribut antarpusat blok, dan
  \(B_k\) = jumlah blok klaster \(k\).
- **Ketegasan partisi**: \(1 - \mathrm{PE}/\ln K\), dengan
  \(\mathrm{PE} = -\frac1N \sum_i \sum_k \tilde u_{ik} \ln \tilde u_{ik}\) dan \(\tilde u\) =
  keanggotaan FCM yang dihitung ulang di ruang atribut pada pusat fuzzy akhir (CATATAN A3).

**Skor komposit** (bobot sama):
\[
S(K) = \tfrac15\big[\mathrm{PR}(I) + \mathrm{PR}(\mathrm{Dunn}) + \mathrm{PR}(\mathrm{DESC})
      + \mathrm{PR}(\mathrm{Ketegasan}) + P(K)\big], \quad
P(K) = 1 - \frac{K - K_{\min}}{K_{\max} - K_{\min}},
\]
dengan PR = *percentile rank* di antara kandidat. K final = \(\arg\max S(K)\) (bila seri, K
terkecil). Tabel lengkap dan selisih skor dengan runner-up disimpan di hasil.

## 9. Penomoran dan penyelarasan label

- **Baseline:** klaster diurutkan naik menurut rata-rata \(t_i^{\min}\) (menit asli); klaster
  0 = akses tercepat.
- **Rendah, Sedang, Tinggi:** pusat fuzzy \(v^{(s)}_k\) di ruang PCA bersama dipasangkan ke
  pusat Baseline \(v^{(0)}_l\) dengan algoritma Hungarian yang meminimalkan
  \(\sum \lVert v^{(s)}_k - v^{(0)}_{\pi(k)}\rVert^2\). Label dan kolom \(U\) dipermutasi sesuai
  \(\pi\).
- Klaster dengan \(\lVert v^{(s)}_k - v^{(0)}_{\pi(k)}\rVert > 2 \cdot \mathrm{median}_{l<l'}
  \lVert v^{(0)}_l - v^{(0)}_{l'}\rVert\) ditandai **tipologi baru/tidak berpadanan**.
- Pada perbandingan algoritma, semua algoritma (termasuk SDWFCM) dinomori ulang menurut rata-rata
  \(t_i^{\min}\) sebelum Moran's I dihitung.

## 10. Metrik transisi (setelah penyelarasan)

Untuk pasangan level berurutan \(a \to b\), matriks transisi \(M_{kl}\) = jumlah grid yang
berlabel \(k\) di \(a\) dan \(l\) di \(b\):

- **Stability rate** \(= 100 \cdot \mathrm{tr}(M)/N\) (%).
- **ARI** (*Adjusted Rand Index*) antara label \(a\) dan \(b\).
- **Transisi dominan** = sel di luar diagonal dengan nilai terbesar.
- **Active edges** = jumlah sel di luar diagonal yang \(> 0\) (dari \(K(K-1)\) kemungkinan).
- **CDVM** (total variation distance terhadap Baseline):
  \(\mathrm{CDVM}(s) = \tfrac12 \sum_k \lvert p_k^{(s)} - p_k^{(0)} \rvert\), dengan \(p_k\) =
  proporsi grid berlabel \(k\).

## 11. Titik Aman Semu (Detour Index)

Untuk tiap grid \(i\), \(e(i)\) = TES valid terdekat secara Euclidean (semua kategori):
\[
T_i^{\text{ideal}} = \frac{\max\big(\lVert c_i - e(i)\rVert,\ 50\ \text{m}\big)}{v}, \qquad
T_i^{\text{aktual}} = \min\!\left(\frac{D^{\text{net}}_{i,e(i)}}{v},\ T_{\text{pen}}\right), \qquad
\mathrm{DI}_i = \frac{T_i^{\text{aktual}}}{T_i^{\text{ideal}}},
\]
dengan \(D^{\text{net}}\) = jarak jaringan antara simpul hasil snapping grid dan TES (snapping ≤ 300 m;
CATATAN A5).

- Grid dengan \(T_i^{\text{aktual}} = T_{\text{pen}}\) → kelas **Terputus** (tidak ikut persentil
  dan rata-rata DI).
- Untuk grid terjangkau \(R\):
\[
\mathrm{TAS}_i \iff T_i^{\text{ideal}} \le P_{25}\big(T^{\text{ideal}}_R\big) \;\wedge\;
\mathrm{DI}_i \ge P_{75}\big(\mathrm{DI}_R\big).
\]
- Dilaporkan: jumlah TAS, Non-TAS, Terputus; rata-rata DI kelompok TAS dan Non-TAS serta
  selisihnya.
- **Uji sensitivitas:** \(T_i^{\text{ideal}} \le P_{25} \wedge \mathrm{DI}_i \ge 2\).

## 12. Perbandingan algoritma (pada Baseline, K final)

Matriks ketetanggaan: rook (fallback queen), grid tanpa tetangga diberi 2 tetangga terdekat,
komponen terputus disambungkan melalui pasangan grid terdekat, dan distandardisasi baris.

- **SFCM**: \(m = 2\), \(\alpha = 0{,}5\); suku spasial \(d^s_{ik}\) = rata-rata \(d^a\)
  tetangga × rata-rata \(u_k\) tetangga; update keanggotaan sama dengan §7.
- **REDCAP**: penggabungan region bertetangga dengan *linkage* Ward, penalti ukuran
  \(n^{1{,}0}\), dan penalti isolasi ×10 bila hanya salah satu region yang rata-rata
  \(t^{\min}\)-nya \(> 30\) menit.
- **SKATER**: `spopt.region.Skater` bila berhasil; jika gagal, MST pada graf ketetanggaan berbobot
  jarak atribut lalu \(K-1\) sisi terberat dipotong (CATATAN C1).

Metrik: Silhouette, Calinski–Harabasz, Davies–Bouldin, WCSS (di ruang PCA), Moran's I label
(99 permutasi, seed 42), *size entropy* \(-\sum_k p_k \ln p_k\), dan **proporsi pasangan
tetangga rook berlabel sama** (tidak bergantung penomoran). Waktu SDWFCM = rata-rata per
inisialisasi.

## 13. Reproduksibilitas

- Seed: SDWFCM 42–51, Dunn 42, Moran 42. Satu thread BLAS/OpenMP.
- Hasil dianggap identik bila hash SHA-256 `thesis_results.json` (tanpa field waktu dan
  `meta.git`) sama; lihat `scripts/cek_reproduksi.py` dan README.

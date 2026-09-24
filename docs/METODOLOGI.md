# Metodologi — sebagaimana diimplementasikan (desain v2)

Dokumen ini menjelaskan pipeline analisis **persis seperti kode** di `backend/engine.py`,
`backend/thesis.py`, dan `scripts/thesis_analysis.py` (tag `hasil-skripsi-v2`). Nilai parameter
yang dipakai pada run final tercatat di `data/locked/LOCK.json`. Hal yang masih perlu diputuskan
tercatat di `docs/CATATAN_TEMUAN.md`. Desain v1 (model per level + penyelarasan Hungarian)
diarsipkan di `data/locked/arsip_v1/` dan `output_bab4/arsip_v1/`.

## 1. Unit analisis dan data

- Unit analisis: grid 100 m × 100 m (\(N = 22.673\)), CRS EPSG:32749. Titik asal setiap grid
  adalah centroid-nya \(c_i\). Setiap grid membawa `id_grid` (0..N−1, urutan baris GPKG, kunci JOIN
  dashboard) dan `id_grid_asli` (kolom `Id` GPKG; bila tidak unik/lengkap diganti ID centroid
  `E{cx}_N{cy}`).
- Atribut grid: kepadatan jaringan jalan `Road_Density_mean` dan kelas bahaya banjir InaRisk
  \(h_i \in \{0,1,2,3\}\).
- Jaringan jalan: 162.608 segmen, masing-masing berkelas bahaya \(c_e \in \{0,1,2,3\}\).
- TES: lima kategori (pendidikan, kesehatan, pemerintahan, ibadah, GOR/gedung serbaguna).

## 2. Level banjir berdasarkan kelas bahaya yang ditutup

Level \(s\) didefinisikan oleh himpunan kelas bahaya yang ditutup \(\mathcal C_s\):

| Level | \(\mathcal C_s\) | Label |
|---|---|---|
| Baseline | \(\varnothing\) | Baseline (tidak ada kelas ditutup) |
| Rendah | \(\{3\}\) | Level Rendah (kelas 3 ditutup) |
| Sedang | \(\{2,3\}\) | Level Sedang (kelas ≥ 2 ditutup) |
| Tinggi | \(\{1,2,3\}\) | Level Tinggi (kelas ≥ 1 ditutup) |

\[
\text{Tergenang}_{i,s} \iff h_i \in \mathcal C_s, \qquad \text{ditutup}_{e,s} \iff c_e \in \mathcal C_s .
\]

*Detail implementasi.* Kode memakai angka intensitas \(I_s\) = 0; 0,25; 0,50; 0,75 dengan aturan
\(p_i = (h_i - h_{\min})/(h_{\max} - h_{\min})\), grid terdampak \(\iff I_s > 0 \wedge p_i \ge 1 - I_s \wedge p_i > 0\),
dan ruas ditutup \(\iff \eta(c_e) I_s \ge 0{,}20\) dengan \(\eta\) = {0: 0; 1: 0,33; 2: 0,67; 3: 1,00}.
`tests/test_level_kelas.py` membuktikan pada data asli bahwa himpunan grid dan ruas yang dihasilkan
**sama persis** dengan aturan kelas di atas untuk keempat level. \(I_s\) juga dipakai sebagai kunci
cache graf jalan di dashboard.

Grid dengan \(\text{Tergenang}_{i,s} = 1\) berstatus **Tergenang** pada level \(s\): dikeluarkan
dari klasterisasi (§6) dan dari deteksi TAS (§11). Waktu tempuhnya tetap dihitung dan disimpan
sebagai informasi, bukan fitur. Himpunan grid Tergenang tidak berkurang saat level naik
(`tests/test_tergenang.py`).

## 3. Filter TES

TES valid bila kelas bahayanya \(< 2\). Pada level dengan grid Tergenang, TES berkelas \(< 2\)
yang berada dalam radius 50 m dari grid Tergenang dinaikkan kelasnya menjadi 3 (tidak valid).

## 4. Waktu tempuh ke TES (dengan ruas snapping) dan penalti

1. Graf jaringan jalan dibentuk dari ruas yang tidak ditutup. Simpul = ujung segmen (dibulatkan
   0,01 m); bobot sisi = panjang segmen (m).
2. Centroid grid dan titik TES di-*snap* ke simpul jalan terdekat bila jaraknya \(\le 300\) m.
   Misalkan \(g(i)\) simpul grid dengan jarak snapping \(a_i\), dan \(n(e)\) simpul TES \(e\)
   dengan jarak snapping \(b_e\).
3. Untuk setiap kategori \(q\) dengan himpunan TES valid \(E_q\) (yang ter-snap):
\[
L_{iq} = a_i + \min_{e \in E_q} \big( D^{\text{net}}_{g(i),\,n(e)} + b_e \big),
\qquad
t_{iq} = \begin{cases} L_{iq}/v & \text{bila terhingga} \\ T_{\text{pen}} & \text{bila tidak} \end{cases},
\qquad v = 80\ \text{m/menit}.
\]
   Implementasi: satu Dijkstra per kategori dari simpul sumber virtual yang dihubungkan ke setiap
   \(n(e)\) dengan bobot \(b_e\) (plus \(10^{-6}\) m karena csgraph mengabaikan bobot 0, lalu
   dikurangkan kembali). Jadi \(t_{iq}\) mengukur perjalanan **centroid grid → titik TES**.
4. \(T_{\text{pen}} = 3\,T_{\max}\), dengan \(T_{\max}\) = waktu tempuh maksimum yang valid
   (terjangkau, \(>0\)) di seluruh kategori pada Baseline. \(T_{\text{pen}}\) dikunci untuk semua level.
5. Variabel turunan:
\[
t_i^{\min} = \min_q t_{iq}, \qquad
\text{opsi}_i = \sum_q \mathbf{1}[t_{iq} < T_{\text{pen}}], \qquad
\text{isolated}_i = \mathbf{1}[\text{opsi}_i = 0].
\]

## 5. Fitur klasterisasi

Sembilan variabel aksesibilitas: `Road_Density_mean`, \(t_{iq}\) untuk lima kategori,
\(t_i^{\min}\), `jumlah_opsi_rute`, dan `is_isolated`. Kelas bahaya banjir \(h_i\) **bukan
fitur**, sehingga tipologi murni menggambarkan aksesibilitas. Kelas bahaya tetap dilaporkan pada
profil klaster sebagai variabel deskriptif. Alasannya: pada data gabungan (§6), grid Tergenang
sudah dikeluarkan, sehingga kelas bahaya grid yang tersisa hampir hanya menandai level. Contohnya,
pada level Tinggi semua grid non-Tergenang berkelas 0.

## 6. Data gabungan dan pra-pemrosesan

**Data gabungan.** Satu baris untuk setiap pasangan (grid \(i\), level \(s\)) dengan
\(\text{Tergenang}_{i,s} = 0\), untuk keempat level. Kolom identitas: `id_grid`, `id_grid_asli`,
`level`. Jumlah baris \(n = \sum_s |\{i : \text{Tergenang}_{i,s} = 0\}|\). Data ini disimpan di
`thesis_pooled_results.csv.gz` (fitur asli, skor PCA, klaster, keanggotaan).

**Pra-pemrosesan** di-fit **sekali** pada data gabungan:

1. Nilai hilang diisi median.
2. Capping Tukey hanya untuk `Road_Density_mean`: \(x \mapsto \min(\max(x, Q_1 - 3\,\mathrm{IQR}), Q_3 + 3\,\mathrm{IQR})\).
3. Seleksi fitur: pertahankan variabel dengan varians \(> 10^{-3}\).
4. Yeo–Johnson per variabel (\(\lambda\) *maximum likelihood*), lalu standardisasi.
5. RobustScaler: \(z' = (z - \mathrm{median}(z)) / \mathrm{IQR}(z)\).
6. PCA dengan jumlah komponen terkecil yang varians kumulatifnya \(\ge 80\%\).

Parameter disimpan sebagai JSON (`preprocessing` di hasil) agar transformasi identik dapat dipakai
ulang oleh simulasi dashboard.

## 7. Matriks bobot spasial blok-diagonal (KNN-Gaussian)

Untuk baris \(r\) pada level \(s\), \(\mathcal N_r\) = 8 tetangga terdekat (jarak centroid
\(\rho_{rj}\)) **di antara baris level \(s\) yang sama**:
\[
\sigma_s = \mathrm{median}\{\rho_{rj} : j \in \mathcal N_r,\ \text{level}(r) = s\}, \qquad
W_{rj} = \frac{\exp(-\rho_{rj}^2 / 2\sigma_s^2)}{\sum_{l \in \mathcal N_r} \exp(-\rho_{rl}^2 / 2\sigma_s^2)}
\quad (j \in \mathcal N_r).
\]
\(W\) blok-diagonal per level: tidak ada tetangga lintas level, dan setiap baris berjumlah 1
(`tests/test_gabungan.py`). \(\sigma_s\) per level tercatat di hasil (`data_gabungan.sigma_per_level`).

## 8. SDWFCM

Parameter: \(m = 1{,}7\), \(\alpha = 0{,}5\), KNN = 8, toleransi \(10^{-4}\), maksimum 150
iterasi, bobot dampak \(\omega = 1{,}0\).

*Bobot dampak nonaktif.* Pada desain v1, \(\omega_j = 2\) untuk tetangga terdampak banjir. Pada
desain gabungan, grid terdampak (Tergenang) sudah dikeluarkan dari data, sehingga tidak ada tetangga
terdampak yang perlu dibobot khusus. `sdwfcm_impact_weight = 1,0` membuat \(\omega_j = 1\) untuk
semua \(j\). Parameter tetap ada di `Cfg` untuk dokumentasi.

Untuk keanggotaan \(U = [u_{rk}]\):
\[
v_k = \frac{\sum_r u_{rk}^m x_r}{\sum_r u_{rk}^m}, \qquad
d^{a}_{rk} = \lVert x_r - v_k \rVert^2, \qquad
d^{s}_{rk} = \frac{\sum_j W_{rj}\,\omega_j\, d^{a}_{jk}\, u_{jk}^m}{\sum_j W_{rj}\, u_{jk}^m}, \qquad
d^{t}_{rk} = (1-\alpha)\, d^{a}_{rk} + \alpha\, d^{s}_{rk},
\]
\[
u_{rk} = \left[ \sum_{l=1}^{K} \left( \frac{d^{t}_{rk}}{d^{t}_{rl}} \right)^{1/(m-1)} \right]^{-1},
\qquad
J(U) = \sum_{r} \sum_{k} u_{rk}^m\, d^{t}_{rk}(U).
\]
Iterasi dimulai dari \(U^{(0)} \sim \mathrm{Dirichlet}(1,\dots,1)\) (seed per inisialisasi) sampai
\(\lVert U^{(t+1)} - U^{(t)} \rVert_F < 10^{-4}\). Label keras \(= \arg\max_k u_{rk}\). Untuk
\(\alpha = 0\) SDWFCM identik dengan FCM baku. Untuk \(\alpha > 0\), \(J\) tidak dijamin turun
monoton (CATATAN B2).

**Multi-start.** 10 inisialisasi (seed 42–51), dipilih solusi dengan \(J\) terkecil.

## 9. Pemilihan K berbasis stabilitas

Aturan ini ditetapkan sebelum melihat hasil. Untuk setiap \(K = 2, \dots, 10\) pada data gabungan:

- **(a) Stabilitas inisialisasi.** 10 run SDWFCM (seed 42–51). \(\overline{\mathrm{ARI}}_{\text{init}}(K)\)
  = rerata ARI dari 45 pasangan run. Solusi data penuh \(\hat L_K\) = run dengan \(J\) terkecil.
- **(b) Stabilitas subsampel.** \(B = 10\) subsampel. Subsampel ke-\(b\) memilih 80% `id_grid` unik
  tanpa pengembalian (seed \(20240 + b\)), dan semua baris (level) dari grid terpilih ikut masuk.
  \(W\) blok-diagonal dihitung ulang pada subsampel. SDWFCM dijalankan 3 inisialisasi (seed 42–44),
  lalu diambil \(J\) terkecil, \(L^{(b)}_K\). Untuk tiap \(b\), \(\mathrm{ARI}_b(K) = \mathrm{ARI}(\hat L_K|_{S_b}, L^{(b)}_K)\)
  dihitung pada baris yang beririsan. Yang dilaporkan: rerata \(\overline{\mathrm{ARI}}_{\text{sub}}(K)\)
  dan simpangan bakunya.

**Aturan keputusan:**
\[
K^\ast = \min\Big\{K : \overline{\mathrm{ARI}}_{\text{sub}}(K) \ge \max_{K'} \overline{\mathrm{ARI}}_{\text{sub}}(K') - 0{,}01\Big\}.
\]
(Bila estimasi waktu satu run melebihi 3 jam, \(B\) diturunkan ke 5. Estimasi pada run final
±2 jam, jadi \(B = 10\); lihat CATATAN P2-C.)

**Metrik pendukung** (dilaporkan, tidak dipakai memilih), dihitung pada \(\hat L_K\):

- **I-Index** (\(p = 2\)) dengan pusat fuzzy \(c_k\):
  \(I(K) = \left(\frac1K \cdot \frac{E_1}{E_K} \cdot D_K\right)^2\).
- **Dunn** titik-ke-titik pada 5 sampel acak 2.000 baris (seed 42–46), dilaporkan rerata dan
  simpangan baku.
- **Ketegasan partisi** \(1 - \mathrm{PE}/\ln K\) pada keanggotaan FCM yang dihitung ulang di ruang
  atribut.
- **DESC/PESC** dengan blok = komponen terhubung baris berlabel sama pada ketetanggaan **rook**
  (§12) yang dibatasi pada level yang sama. \(\mathrm{DESC} = \sum_{b,|b|\ge 2} V_b^2/\delta_b^2\),
  \(\mathrm{PESC} = \sum_k \sum_{b<b'} V_b V_{b'} / (S_{bb'} \Delta_{bb'} B_k)\), dengan \(S\) dalam km.
- **Silhouette** pada sampel 10.000 baris (seed 42).
- **Analisis sensitivitas:** skor komposit lama \(\tfrac15[\mathrm{PR}(I) + \mathrm{PR}(\mathrm{Dunn})
  + \mathrm{PR}(\mathrm{DESC}) + \mathrm{PR}(\mathrm{Ketegasan}) + P(K)]\), dan versi tanpa DESC
  (rerata empat suku). \(P(K) = 1 - (K - 2)/8\).

## 10. Penomoran dan status per level

Klaster diurutkan naik menurut rata-rata \(t^{\min}\) (menit, termasuk ruas snapping) pada data
gabungan. Klaster 0 = akses terbaik. Tidak ada penyelarasan antarlevel, karena satu model berlaku
untuk semua level. Mekanisme Hungarian dan penanda "tipologi baru" v1 dihapus.

Status grid \(i\) pada level \(s\):
\[
z_{i,s} = \begin{cases} \text{label}(i,s) \in \{0,\dots,K-1\} & \text{bila } \text{Tergenang}_{i,s} = 0 \\
K\ (\text{Tergenang}) & \text{bila } \text{Tergenang}_{i,s} = 1 \end{cases}.
\]
Profil klaster = rata-rata variabel asli per klaster atas seluruh baris data gabungan. Distribusi
tipologi per level = jumlah grid per state \(z_{\cdot,s}\).

## 11. Titik Aman Semu (Detour Index)

Untuk grid \(i\) pada level \(s\), \(e(i)\) = TES valid terdekat secara Euclidean (semua kategori):
\[
T_i^{\text{ideal}} = \frac{\max\big(\lVert c_i - e(i)\rVert,\ 50\ \text{m}\big)}{v}, \qquad
T_i^{\text{aktual}} = \min\!\left(\frac{\max\big(a_i + D^{\text{net}}_{g(i),\,n(e(i))} + b_{e(i)},\ 50\ \text{m}\big)}{v},\ T_{\text{pen}}\right),
\qquad \mathrm{DI}_i = \frac{T_i^{\text{aktual}}}{T_i^{\text{ideal}}}.
\]
Kedua waktu mengukur perjalanan centroid → titik TES dengan batas minimum 50 m yang sama. Karena
itu \(T^{\text{aktual}} \ge T^{\text{ideal}}\) untuk semua grid terjangkau (ketaksamaan segitiga;
diuji pada data asli). Batas 50 m pada \(T^{\text{aktual}}\) adalah keputusan pengguna (CATATAN P2-B2).

Kategori per level:

- **Tergenang**: \(\text{Tergenang}_{i,s} = 1\), dikeluarkan dari seluruh perhitungan TAS.
- **Terputus**: non-Tergenang dengan \(T^{\text{aktual}} = T_{\text{pen}}\).
- Untuk himpunan \(R\) = grid non-Tergenang yang terjangkau:
\[
\mathrm{TAS}_i \iff T_i^{\text{ideal}} \le P_{25}\big(T^{\text{ideal}}_R\big) \;\wedge\;
\mathrm{DI}_i \ge P_{75}\big(\mathrm{DI}_R\big),
\]
  selebihnya **Non-TAS**.
- **Uji sensitivitas:** \(T_i^{\text{ideal}} \le P_{25} \wedge \mathrm{DI}_i \ge 2\). Dilaporkan
  juga persentase TAS yang juga lolos ambang absolut ini.

## 12. Analisis transisi dengan state Tergenang

Untuk pasangan Baseline→Rendah, Rendah→Sedang, Sedang→Tinggi, dan Baseline→Tinggi
(\(a \to b\)), matriks \(M \in \mathbb{N}^{(K+1)\times(K+1)}\) dengan \(M_{kl} = |\{i : z_{i,a} = k,\ z_{i,b} = l\}|\):

- **Masuk Tergenang** \(= |\{i : z_{i,a} < K,\ z_{i,b} = K\}|\), dalam jumlah dan persentase
  (terhadap semua grid dan terhadap grid non-Tergenang di \(a\)).
- Dengan \(G = \{i : z_{i,a} < K \wedge z_{i,b} < K\}\) (non-Tergenang di kedua level):
  **stability rate** \(= 100 \cdot \sum_{k<K} M_{kk} / |G|\), dan **ARI** \(= \mathrm{ARI}(z_{G,a}, z_{G,b})\).
- **Transisi dominan** = sel di luar diagonal \(M\) dengan nilai terbesar, disertai keterangan
  menuju Tergenang atau tipologi lain.
- **Active edges** = jumlah sel di luar diagonal \(M\) yang \(> 0\), dari \((K+1)K\) kemungkinan.
- **CDVM** = total variation distance distribusi state:
  \(\tfrac12 \sum_{u=0}^{K} \lvert p_u^{(b)} - p_u^{(a)} \rvert\).

## 13. Perbandingan algoritma (Baseline, \(K^\ast\))

Data: baris Baseline dari data gabungan (semua grid; ruang PCA dan praproses yang sama). Algoritma
fuzzy memakai \(K^\ast\), 10 inisialisasi (seed 42–51, \(J\) terkecil), dan aturan penomoran §10:

- **FCM**: SDWFCM dengan \(\alpha = 0\) (\(m = 1{,}7\)).
- **SFCM**: \(m = 2\), \(\alpha = 0{,}5\). \(d^s_{ik}\) = (rata-rata \(d^a\) tetangga rook) ×
  (rata-rata \(u_k\) tetangga rook); grid tanpa tetangga memakai \(d^s = d^a\). Seleksi inisialisasi
  memakai \(J_{\text{SFCM}} = \sum u^m d^t\). Implementasi tervektorisasi dengan operator rata-rata
  tetangga, identik dengan rumus per grid (`tests/test_gabungan.py`).
- **SDWFCM**: §8 dengan \(W\) blok Baseline.
- **REDCAP** (satu run deterministik): penggabungan region bertetangga dengan *linkage* Ward,
  penalti ukuran \(n^{1{,}0}\), dan penalti isolasi ×10.
- **SKATER**: `spopt.region.Skater` dengan ukuran region minimum `floor` = 10 pada ketetanggaan rook
  biner simetris. Tidak ada fallback. Bila spopt gagal, galatnya dilaporkan.

Partisi dengan klaster terbesar \(> 90\%\) grid ditandai **degeneratif (tidak layak dibandingkan)**.
Metrik: Silhouette, Calinski–Harabasz, Davies–Bouldin (ruang PCA), Moran's I label (999 permutasi,
seed permutasi 42, kontiguitas rook), proporsi pasangan tetangga rook berlabel sama, *size entropy*,
ukuran klaster terbesar (%), dan waktu per inisialisasi.

Ketetanggaan rook (`build_weights`): rook (fallback queen), grid tanpa tetangga diberi 2 tetangga
terdekat, dan komponen terputus disambungkan melalui pasangan grid terdekat.

## 14. Simulasi blokir jalan di dashboard (bukan hasil skripsi)

Dashboard menghitung ulang aksesibilitas level terpilih dengan ruas yang diblokir pengguna, lalu
menerapkan praproses data gabungan (parameter tersimpan). Keanggotaan dihitung terhadap **pusat
klaster final yang tetap**: iterasi \(U\) dengan \(d^t\) pada §8 dan \(W\) KNN-Gaussian level
tersebut, sedangkan pusat tidak diperbarui. Model tidak di-fit ulang, sehingga nomor klaster tetap
bermakna sama.

## 15. Reproduksibilitas

- Seed: SDWFCM/FCM/SFCM 42–51, subsampel \(20240 + b\), Dunn 42–46, Silhouette 42, permutasi Moran 42.
  Satu thread BLAS/OpenMP.
- Hasil dianggap identik bila fingerprint `thesis_results.json` (tanpa field waktu dan `meta.git`)
  dan SHA-256 isi CSV grid dan data gabungan sama; lihat `scripts/cek_reproduksi.py` dan README.

# Metodologi — sebagaimana diimplementasikan (hasil v6)

Dokumen ini menjelaskan pipeline analisis **persis seperti kode** di `backend/engine.py`,
`backend/hazard_raster.py`, `backend/thesis.py`, dan `scripts/thesis_analysis.py` (tag
`hasil-skripsi-v6`; snapping ke ruas terdekat, pemilihan K dihitung ulang, atribusi banjir pada TAS; ambang
dan aturan lain sama dengan v5). Rujukan setiap parameter beserta status verifikasinya: `docs/RUJUKAN_PARAMETER.md`. Nilai parameter yang dipakai pada run final tercatat di `data/locked/LOCK.json`.
Hal yang masih perlu diputuskan tercatat di `docs/CATATAN_TEMUAN.md`. Versi sebelumnya diarsipkan:
v1 di `data/locked/arsip_v1/` (model per level + Hungarian) dan v2 di `data/locked/arsip_v2/`
(kelas bahaya grid dari atribut GPKG, aturan TAS persentil, keluaran K = 2 saja), dan v3 di
`data/locked/arsip_v3/` (keluaran K = 2 dan 3, label ambang median, TAS tanpa syarat T_aktual), v4 di
`data/locked/arsip_v4/`, dan v5 di `data/locked/arsip_v5/` (snapping ke verteks terdekat).

## 1. Unit analisis dan data

- Unit analisis: grid 100 m × 100 m (\(N = 22.673\)), CRS EPSG:32749. Titik asal setiap grid
  adalah centroid-nya \(c_i\). Setiap grid membawa `id_grid` (0..N−1, urutan baris GPKG, kunci JOIN
  dashboard) dan `id_grid_asli` (kolom `Id` GPKG; bila tidak unik/lengkap diganti ID centroid
  `E{cx}_N{cy}`).
- Atribut grid: kepadatan jaringan jalan `Road_Density_mean`.
- Jaringan jalan: 162.608 segmen OSM.
- TES: lima kategori (pendidikan, kesehatan, pemerintahan, ibadah, GOR/gedung serbaguna).
- **Kelas bahaya banjir** \(h \in \{0,1,2,3\}\) untuk grid, ruas, dan TES diturunkan dari **satu
  sumber**, yaitu raster InaRisk `data/Kulonprogo_Banjir.tif` (EPSG:32749, piksel 29,71 m; 1 = rendah,
  2 = sedang, 3 = tinggi; nodata = 0):
  - grid \(h_i\): kelas **mayoritas** piksel yang pusatnya berada di dalam grid (kelas 0 ikut
    dihitung; seri → kelas terendah; grid tanpa pusat piksel → piksel di centroid);
  - ruas \(c_e\): kelas **maksimum** piksel sepanjang segmen (sampel titik tiap ≤ 5 m, termasuk
    kedua ujung);
  - TES: nilai piksel di titik TES.

  Atribut `banjir` bawaan GPKG diganti hasil turunan ini saat data dimuat, dan disimpan sebagai
  `banjir_atribut_lama`. Alasan dan uji asal-usul: `docs/DIAGNOSTIK_JALAN_GRID.md`.

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
2. **Snapping ke ruas (Putaran 6, koreksi metode hasil validasi).** Centroid grid dan titik TES
   di-*snap* ke titik terdekat pada **ruas** jalan yang terbuka pada level tersebut (proyeksi tegak
   lurus ke sisi graf, dicari dengan shapely STRtree) bila jaraknya \(\le 300\) m. Pada titik
   proyeksi disisipkan simpul virtual, dan sisi itu dipecah menjadi sisi-sisi berurutan dengan bobot
   proporsional terhadap panjangnya (titik-titik pada sisi yang sama diurutkan menurut posisinya;
   total bobot pecahan = bobot sisi asli). Proyeksi yang jatuh ≤ 1 mm dari ujung sisi memakai simpul
   ujung itu. Bila beberapa ruas sama dekat, dipilih sisi berindeks terkecil (deterministik).
   Misalkan \(g(i)\) simpul (virtual) grid dengan jarak snapping tegak lurus \(a_i\), dan \(n(e)\)
   simpul (virtual) TES \(e\) dengan jarak snapping \(b_e\). Grid/TES tanpa ruas terbuka dalam
   300 m diperlakukan seperti sebelumnya (tidak terjangkau → penalti).
   Sampai v5, titik di-*snap* ke **verteks** jalan terdekat. Validasi manual TAS v5 menunjukkan cara
   itu dapat menyambungkan titik ke jalan di seberang penghalang walaupun ada ruas lain yang lebih
   dekat (ruas panjang tanpa verteks tengah); lihat CATATAN Putaran 6 (P6-1).
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

### 8a. Perbedaan dengan Guo dkk. (2015): "SDWFCM termodifikasi"

Rujukan: Guo, Liu, Wu, Hong, & Zhang (2015), *A new spatial fuzzy c-means for spatial clustering*, WSEAS
Transactions on Computers 14, 369–381. Implementasi skripsi disebut **SDWFCM termodifikasi**. Versi harfiah
artikel diimplementasikan terpisah sebagai pembanding (`backend/sdwfcm_guo.py`, "SDWFCM-Guo").

**Rumus asli Guo dkk. (hlm. 372, pers. 7–10).** Dengan \(d_{ij} = \lVert x_j - v_i\rVert\) (jarak Euclidean,
tidak dikuadratkan) dan \(NB(j)\) = tetangga spasial sampel \(j\):
\[
f_{ij} = \frac{\sum_{k \in NB(j)} d_{ik}}{\min_{l} \sum_{k \in NB(j)} d_{lk}}, \qquad
D_{ij} = (1-\lambda)\, d_{ij}\, f_{ij} + \lambda\, d_{ij}, \qquad
u_{ij} = \left[\sum_{k=1}^{c} \left(\frac{D_{ij}}{D_{kj}}\right)^{1/(m-1)}\right]^{-1}.
\]

**Rumus yang diimplementasikan (§8).** \(d^t = (1-\alpha)\, d^a + \alpha\, d^s\), dengan \(d^a\) jarak
Euclidean **kuadrat** dan \(d^s\) rata-rata tertimbang \(d^a\cdot u^m\) tetangga dengan bobot Gaussian
KNN-8 (blok-diagonal per level).

**Perbedaan dan alasannya:**

1. **Penjumlahan vs perkalian.** Guo memakai faktor spasial perkalian (\(d\cdot f\)), yaitu rasio jumlah jarak
   tetangga terhadap minimumnya. Implementasi memakai penjumlahan jarak atribut dan jarak spasial tertimbang,
   sehingga suku spasial berada pada satuan yang sama dengan \(d^a\) dan bobotnya dikendalikan langsung
   oleh \(\alpha\).
2. **Bobot kontinu.** Tetangga diberi bobot Gaussian menurut jarak, bukan himpunan tetangga biner.
   Keanggotaan tetangga ikut sebagai bobot (\(u^m\)).
3. **Fungsi objektif.** Implementasi merumuskan \(J(U) = \sum u^m d^t\). J dipakai untuk memilih solusi
   multi-start dan untuk memeriksa konvergensi secara **empiris**: kriteria henti \(\lVert\Delta U\rVert_F <
   10^{-4}\) tercapai, dan \(J\) turun hampir monoton, dengan kenaikan relatif ± \(10^{-7}\) pada beberapa
   iterasi akhir (CATATAN B2; uji `xfail`). Konvergensi **tidak terbukti secara teoretis**. Artikel Guo tidak
   merumuskan fungsi objektif.
4. **Pangkat keanggotaan.** Implementasi memakai \(1/(m-1)\) pada jarak **kuadrat**, setara dengan FCM baku.
   Artikel menulis \(1/(m-1)\) pada \(D\) yang dibentuk dari jarak **tak-kuadrat**. Ini ambigu: bila dibaca
   harfiah, bentuknya berbeda dari FCM baku (Bezdek), yang memakai pangkat \(2/(m-1)\) pada jarak
   tak-kuadrat. Karena itu SDWFCM-Guo dijalankan dalam bentuk harfiah dan dalam varian \(d^2\).
5. **Inkonsistensi λ pada artikel.** Teks menyatakan informasi spasial makin berperan saat \(\lambda \to 1\)
   (hlm. 372). Namun pada \(\lambda = 1\) rumus (9) menjadi \(D = d\), sehingga faktor spasial hilang.
   Menurut rumusnya, peran spasial justru membesar saat \(\lambda \to 0\). Artikel melaporkan hasil terbaik
   pada \(\lambda = 0{,}5\) (hlm. 375), dan nilai itulah yang dipakai untuk SDWFCM-Guo. Varian
   \(\lambda = 0{,}3\) dan \(0{,}7\) dilaporkan sebagai sensitivitas.
6. **Kriteria henti.** Artikel berhenti bila perubahan pusat klaster memenuhi kriteria (langkah 6). Atas
   instruksi Finalisasi v6, kedua versi memakai kriteria henti model utama, dan SDWFCM-Guo memilih run dengan
   \(J_{FCM} = \sum u^m \lVert x - v\rVert^2\) terkecil.

Hasil perbandingan pada Baseline (T06/S06, L02): {{HASIL_GUO}}

### 8b. DESC-N dan PESC-N (modifikasi Guo dkk., 2015)

DESC dan PESC asli (Guo dkk., 2015, hlm. 374, pers. 11–14) dirancang untuk membandingkan algoritma pada K tetap.
Keduanya tidak dapat dibandingkan antar-K:

- DESC melonjak dari 0,07 (K = 3) ke 74,9 (K = 4), lalu naik monoton.
- PESC tidak stabil (hingga 15.382).

Dugaan penyebabnya:

- pembagi \(\bar d\) (DESC) dan \(D\cdot d\) (PESC) mendekati nol pada blok beratribut hampir identik;
- tidak ada normalisasi terhadap K;
- satuan bergantung skala.

Catatan implementasi repo: DESC di repo mengabaikan blok satu sampel, sedangkan artikel memakai
\(\bar d = 1\) untuk blok satu sampel. PESC di repo memakai jarak antarpusat blok (km), sedangkan artikel memakai
jarak pasangan sampel terdekat.

**Diagnostik (B1).** {{HASIL_B1}}

**Definisi (ditetapkan sebelum dihitung; `backend/desc_n.py`).** Blok = komponen terhubung baris ber-label sama
(label tegas) pada ketetanggaan rook, dihitung per level lalu digabung. Notasi:

- \(N\) = jumlah baris non-Tergenang; \(Cn_k\) = ukuran klaster \(k\);
- \(v_i\) = ukuran blok \(i\); \(V_i = v_i/Cn_k\);
- \(\bar d_i\) = rata-rata jarak atribut anggota blok ke pusat blok;
- \(s\) = rata-rata jarak Euclidean semua baris ke pusat global (satu konstanta per data);
- \(g(x) = 1/(1+x^2)\).

\[
\tilde d_i = \begin{cases} \bar d_i / s & v_i \ge 2 \\ 1 & v_i = 1 \end{cases}, \qquad
\mathrm{DESC\text{-}N} = \sum_k \frac{Cn_k}{N} \sum_{i \in k} V_i^2\, g(\tilde d_i),
\]
dengan dua komponen
\[
\mathrm{Kontiguitas} = \sum_k \frac{Cn_k}{N} \sum_{i\in k} V_i^2, \qquad
\mathrm{Homogenitas} = \sum_k \frac{Cn_k}{N} \cdot \frac{\sum_{i\in k} v_i\, g(\tilde d_i)}{Cn_k},
\]
\[
\mathrm{PESC\text{-}N} = \sum_k \frac{Cn_k}{N} P_k, \qquad
P_k = \begin{cases} \dfrac{\sum_{i<j} V_i V_j\, \tilde D_{ij}^{-1}\, g(\tilde d_{ij})}{\sum_{i<j} V_i V_j} & Bn_k \ge 2 \\[1ex] 1 & Bn_k = 1 \end{cases},
\]
dengan \(\tilde D_{ij}\) = jarak terdekat antara sel-sel blok \(i\) dan \(j\) dibagi 100 m (minimal 1), dan
\(\tilde d_{ij}\) = jarak atribut antarpusat blok dibagi \(s\). Keduanya bernilai \((0, 1]\); makin besar makin
baik.

**Alasan setiap modifikasi:**

- \(g\) terbatas dan \(g(0) = 1\), sehingga tidak meledak bila \(\bar d = 0\).
- Pembagian dengan \(s\) membuat metrik invarian terhadap skala atribut.
- Bobot \(Cn_k/N\) dan \(V_i = v_i/Cn_k\) menormalisasi terhadap K dan ukuran klaster.
- \(\tilde D\) dalam satuan sel (minimal 1) menghindari pembagian dengan nol.
- PESC-N dinormalisasi dengan \(\sum V_iV_j\) sehingga menjadi rata-rata tertimbang.

Perhitungan PESC-N eksak bila jumlah pasangan per klaster ≤ 2 juta. Bila lebih, pasangan antarblok berukuran
≥ 2 dihitung eksak dan sisanya diperkirakan dengan 200.000 pasangan acak berbobot \(V_iV_j\) (seed 42).
Pada data gabungan, pasangan blok lintas level ikut dihitung dengan jarak pada koordinat grid.

**Validasi data buatan (B3).** {{HASIL_B3}}

## 9. Pemilihan K berbasis stabilitas

Untuk setiap \(K = 2, \dots, 10\) pada data gabungan:

- **(a) Stabilitas inisialisasi.** 10 run SDWFCM (seed 42–51). \(\overline{\mathrm{ARI}}_{\text{init}}(K)\)
  = rerata ARI dari 45 pasangan run. Solusi data penuh \(\hat L_K\) = run dengan \(J\) terkecil.
- **(b) Stabilitas subsampel.** \(B = 10\) subsampel. Subsampel ke-\(b\) memilih 80% `id_grid` unik
  tanpa pengembalian (seed \(20240 + b\)), dan semua baris (level) dari grid terpilih ikut masuk.
  \(W\) blok-diagonal dihitung ulang pada subsampel. SDWFCM dijalankan 3 inisialisasi (seed 42–44),
  lalu diambil \(J\) terkecil. Untuk tiap \(b\) dihitung ARI terhadap \(\hat L_K\) pada baris yang
  beririsan. Yang dilaporkan: rerata \(\overline{\mathrm{ARI}}_{\text{sub}}(K)\) dan simpangan bakunya.

Pada putaran 3, evaluasi ini **dihitung ulang** pada data v3 (kelas bahaya dari raster) atas keputusan
peneliti, karena data gabungan berubah.

**Riwayat keputusan (ditulis apa adanya):**

- **(a) Aturan stabilitas.** Aturan ini ditetapkan di Putaran 2 sebelum hasil v2 terlihat:
  \[
  K^\ast = \min\Big\{K : \overline{\mathrm{ARI}}_{\text{sub}}(K) \ge \max_{K'} \overline{\mathrm{ARI}}_{\text{sub}}(K') - 0{,}01\Big\}.
  \]
  Artinya, K dengan rerata ARI subsampel tertinggi dipilih, dengan pemecah seri "K terkecil" bila
  beberapa K berselisih ≤ 0,01. Pada hasil v2, aturan ini memilih **K = 2**.
- **(b) K = 2 dan K = 3 tidak dapat dibedakan secara stabilitas.** Pada v2, rerata ARI subsampel
  K = 2 0,964 ± 0,006 dan K = 3 0,963 ± 0,003. Selisih 0,001 lebih kecil dari simpangan baku kedua K,
  jadi pilihan K = 2 hanya ditentukan pemecah seri.
  **Pada data v3** (kelas bahaya dari raster), evaluasi ulang memberi K = 2 0,957 ± 0,004, K = 4
  0,949 ± 0,003 (setara, selisih ≤ 0,01), dan K = 3 0,940 ± 0,006 (tidak setara, selisih 0,017).
  Aturan tetap memilih K = 2. Kesetaraan K = 2 dan K = 3 yang menjadi alasan membandingkan keduanya
  hanya berlaku untuk data v2.
- **(c) Model utama ditetapkan kemudian.** Keputusan model utama diambil peneliti bersama pembimbing
  **setelah** hasil terlihat. Keputusan ini bukan bagian dari rencana awal. Setelah hasil v2 terlihat,
  v3 menyusun keluaran lengkap untuk K = 2 dan K = 3. Setelah hasil v3 terlihat, himpunan K yang
  **setara secara stabilitas** dengan K terbaik (selisih rerata ARI subsampel ≤ 0,01) adalah {2, 4}.
  Dari himpunan itu, peneliti memilih model utama berdasarkan metrik pendukung dan interpretasi
  tipologi. Putaran 4 menyusun keluaran lengkap dengan struktur identik untuk **K = 2, 3, dan 4**.
  K = 3 dipertahankan sebagai pembanding dari v3, meskipun tidak setara secara stabilitas. K utama
  dicatat di `pengaturan_hasil.json` (dibaca `scripts/export_bab4.py` dan dashboard); K lainnya
  dilaporkan sebagai sensitivitas.
- **(e) Model utama: K = 4 (Putaran 5).** Peneliti menetapkan **K = 4** sebagai model utama
  **setelah** hasil v3 dan v4 terlihat. Pilihan diambil dari himpunan K yang setara secara stabilitas
  dengan K terbaik (selisih rerata ARI subsampel ≤ 0,01; pada data v3: {2, 4}). Alasannya: K = 4
  memisahkan tipologi grid Terputus. Tipologi 4 berisi 1,8% baris data gabungan, 96,3% di antaranya
  bernilai penalti (CATATAN P4-7). K = 2 (pilihan aturan stabilitas dengan pemecah seri "K terkecil")
  dan K = 3 (tidak setara secara stabilitas) dilaporkan sebagai sensitivitas. Keputusan ini tidak
  mengubah model, data, maupun ambang apa pun.
- **(d) Pemilihan K tidak dijalankan ulang pada Putaran 4.** Tabel stabilitas v3 dipakai apa adanya,
  setelah pipeline memverifikasi bahwa data gabungan (baris, level, dan skor PCA) identik dengan v3
  (`verifikasi_v3` di hasil). Model K = 2, 3, dan 4 adalah solusi J terkecil dari seed 42–51 pada data
  gabungan, praproses, dan W yang sama; label K = 2 dan K = 3 diverifikasi identik dengan v3.

- **(f) Pemilihan K dihitung ulang pada Putaran 6.** Koreksi snapping (§4) mengubah waktu tempuh, sehingga
  data gabungan berbeda dari v3/v5 dan tabel stabilitas v3 tidak lagi berlaku. Evaluasi stabilitas (a)–(b)
  dijalankan ulang pada data v6 dengan aturan, seed, dan jumlah subsampel yang sama. Aturan K utama
  ditetapkan peneliti **sebelum** hasil v6 terlihat: K utama tetap 4 bila K = 4 masih termasuk himpunan
  setara stabilitas (selisih rerata ARI subsampel ≤ 0,01 dari K terbaik); bila tidak, analisis berhenti
  dan keputusan dikembalikan ke peneliti. Model K = 2, 3, dan 4 = solusi \(J\) terkecil dari seed 42–51
  (solusi data penuh evaluasi stabilitas).

- **(h) Kriteria akhir pemilihan K (Finalisasi v6; menggantikan (e) dan peran stabilitas sebagai aturan
  utama).** Peneliti bersama pembimbing menetapkan **K utama = 4**. Rinciannya di `docs/KEPUTUSAN_K_v6.md`.
  - **Kriteria:** K dipilih dengan indeks validitas **I-Index, Dunn, dan ketegasan partisi**, sesuai rancangan
    awal penelitian (draft) yang merujuk Guo dkk. (2015). Pada v6, I-Index (15,218) dan ketegasan partisi
    (0,457) tertinggi pada K = 4. Dunn tertinggi pada K = 5 (0,0107), dengan selisih sangat kecil dari K = 4
    (0,0105; sampel 2.000 baris).
  - **Metrik yang dikecualikan:** DESC dan PESC asli tidak dipakai memilih K karena tidak dinormalisasi
    terhadap jumlah klaster. DESC naik monoton sejak K = 4 (0,07 pada K = 3 → 74,9 pada K = 4 → 85,2 pada
    K = 10), dan PESC tidak stabil (hingga 15.382). Versi ternormalisasinya (DESC-N, PESC-N; §8b) hanya
    dilaporkan sebagai metrik pendukung.
  - **Uji ketahanan:** stabilitas subsampel kini dipakai sebagai uji ketahanan, bukan aturan pemilihan.
    K = 4 memiliki ARI subsampel 0,948 ± 0,004, berselisih 0,011 dari K = 2 (0,959). Pemeriksaan
    one-standard-error juga menunjuk K = 2 (`KEPUTUSAN_K_v6.md` (b)).
  - **Riwayat (ditulis apa adanya):** kriteria stabilitas menjadi aturan utama pemilihan K pada v2–v6 dan
    menunjuk K = 2 pada v6 (himpunan setara {2}; CATATAN P6-6). Kriteria akhir di atas **ditetapkan setelah
    hasil v6 terlihat**, bukan direncanakan sejak awal rekonstruksi. Butir (g) tidak pernah ada. Butir (e)
    (K = 4 dipilih dari himpunan setara stabilitas {2, 4} pada v3) digantikan oleh butir ini, karena pada
    v6 himpunan tersebut tidak lagi memuat K = 4.
  - **Catatan interpretasi:** lonjakan I-Index pada K = 4 bertepatan dengan terbentuknya klaster baris
    bernilai penalti (Tipologi 4, 1,73 % baris, 96,5 % Terputus). Pusat klaster itu jauh dari pusat lain
    sehingga DK membesar.

**Metrik pendukung** pada \(\hat L_K\), ditampilkan di tabel utama: Silhouette (sampel 10.000 baris,
seed 42), ketegasan partisi \(1 - \mathrm{PE}/\ln K\) (keanggotaan FCM dihitung ulang di ruang
atribut), *size entropy*, dan ukuran klaster terbesar (%).

**Lampiran** (dilaporkan, tidak dipakai memilih):

- I-Index (\(p = 2\)) dengan pusat fuzzy;
- Dunn pada 5 sampel 2.000 baris (seed 42–46), rerata dan simpangan baku;
- DESC/PESC dengan blok rook yang dibatasi pada level yang sama;
- skor komposit lama \(\tfrac15[\mathrm{PR}(I) + \mathrm{PR}(\mathrm{Dunn}) + \mathrm{PR}(\mathrm{DESC}) +
  \mathrm{PR}(\mathrm{Ketegasan}) + P(K)]\) dan versi tanpa DESC, dengan \(P(K) = 1 - (K-2)/8\).

## 10. Penomoran dan status per level

Klaster diurutkan naik menurut rata-rata \(t^{\min}\) (menit, termasuk ruas snapping) pada data
gabungan. Klaster 0 = akses terbaik. Tidak ada penyelarasan antarlevel, karena satu model berlaku
untuk semua level. Mekanisme Hungarian dan penanda "tipologi baru" v1 dihapus.

Status grid \(i\) pada level \(s\):
\[
z_{i,s} = \begin{cases} \text{label}(i,s) \in \{0,\dots,K-1\} & \text{bila } \text{Tergenang}_{i,s} = 0 \\
K\ (\text{Tergenang}) & \text{bila } \text{Tergenang}_{i,s} = 1 \end{cases}.
\]
**Profil klaster** (untuk setiap K keluaran), dihitung atas seluruh baris data gabungan:

- rerata semua variabel;
- untuk setiap variabel waktu (lima kategori dan waktu minimum): median, P25, P75, dan P90;
- jumlah dan persentase baris bernilai penalti \(t = T_{\text{pen}}\), per kategori dan untuk waktu
  minimum;
- proporsi baris dengan \(t^{\min} >\) 30 menit (dan 20/40 menit) serta proporsi baris Terputus;
- proporsi grid terisolasi (`is_isolated`).

Kelas bahaya banjir hanya dilaporkan sebagai variabel deskriptif.

**Label tipologi (Putaran 4: perubahan penyajian, bukan perubahan model).** Klaster \(k\) (urutan
rata-rata \(t^{\min}\) naik) diberi label peringkat **"Tipologi \(k+1\)"**, dengan Tipologi 1 =
terbaik dan Tipologi K = terburuk. Label berbasis ambang median pada v3 ("Terisolasi" bila > 50%
baris penalti; median ≤ 10 menit "Akses Baik", 10–30 "Akses Sedang", > 30 "Akses Kritis") diganti
karena tidak membedakan klaster: kedua klaster K = 2 mendapat label "Akses Baik" (CATATAN P3-9).
Model, keanggotaan, dan penomoran tidak berubah.

Profil yang wajib dibaca bersama label peringkat: median, P75, dan P90 waktu minimum; persentase
baris penalti; proporsi baris dengan \(t^{\min} >\) batas waktu evakuasi (30 menit; juga 20 dan 40);
proporsi baris **Terputus** (\(t^{\min} = T_{\text{pen}}\)); dan proporsi grid terisolasi.

Distribusi tipologi per level = jumlah grid per state \(z_{\cdot,s}\). Tabulasi silang label pada baris
data gabungan disusun untuk setiap pasangan K keluaran (K = 2 × 3, 2 × 4, 3 × 4).

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
- **TES terdekat tidak terjangkau** (sebelum Putaran 5 bernama "Terputus"): non-Tergenang dengan
  \(T^{\text{aktual}} = T_{\text{pen}}\). TES terdekat secara garis lurus \(e(i)\) tidak dapat dicapai
  lewat jaringan jalan (gagal snapping ≤ 300 m atau tidak terhubung).
- **Aturan utama (Putaran 4).** Untuk \(R\) = grid non-Tergenang yang terjangkau:
\[
\mathrm{TAS}_i \iff \mathrm{DI}_i \ge 2 \;\wedge\; T_i^{\text{ideal}} \le 5\ \text{menit}
\;\wedge\; T_i^{\text{aktual}} \ge T_{\text{evak}},\qquad T_{\text{evak}} = 30\ \text{menit},
\]
  selebihnya **Non-TAS**. \(T_{\text{evak}}\) adalah batas waktu evakuasi berjalan kaki (Li dkk.,
  2026, hlm. 2915; Park dkk., 2020, hlm. 5). Semua ambang ditetapkan sebelum hasil v4 terlihat.
  Artinya, TAS adalah grid yang TES-nya tampak dekat (garis lurus ≤ 400 m), tetapi perjalanan
  jaringannya minimal dua kali garis lurus dan melebihi batas waktu evakuasi.
- **Sensitivitas:** (i) \(T^{\text{aktual}} \ge 20\) dan \(\ge 40\) menit (Li dkk., 2026, hlm. 2920),
  termasuk proporsi TAS utama yang tetap TAS pada kedua ambang (irisan); (ii) aturan absolut v3
  (tanpa syarat \(T^{\text{aktual}}\)); (iii) aturan persentil v2
  (\(T^{\text{ideal}} \le P_{25} \wedge \mathrm{DI} \ge P_{75}\) pada \(R\)).
- **Perubahan TAS terhadap Baseline (aturan utama):** *TAS baru akibat banjir* = grid yang bukan TAS di
  Baseline dan menjadi TAS di level \(s\); *TAS hilang* = grid TAS di Baseline yang tidak lagi TAS di
  level \(s\), dipecah menjadi jadi Tergenang, jadi TES terdekat tidak terjangkau, dan lainnya (Non-TAS).
- **Yang dilaporkan:** jumlah TAS, Non-TAS, TES terdekat tidak terjangkau, dan Tergenang per level; sebaran DI (median,
  P25, P75, P90) pada TAS dan Non-TAS; median \(T^{\text{ideal}}\) dan \(T^{\text{aktual}}\) TAS;
  jumlah TAS per kategori TES terdekat (\(e(i)\)); peta TAS per level; dan peta TAS baru/hilang untuk
  Sedang dan Tinggi.
- **Batasan interpretasi.** Perbedaan DI antara TAS dan Non-TAS mengikuti langsung dari definisi
  aturan, sehingga tidak dipakai sebagai bukti keberhasilan deteksi. Tabel TAS tidak bergantung pada K.

## 11b. Kategori akses per level (padanan Li dkk., 2026)

Klasifikasi tambahan per grid per level. Klasterisasi tidak berubah. Istilah mengikuti kategori
komunitas tanpa akses pada Li dkk. (2026, hlm. 2919):

| Kategori | Padanan Li dkk. (2026) | Definisi |
|---|---|---|
| Tergenang | *flooded* | \(\text{Tergenang}_{i,s} = 1\) |
| Terputus | *isolated* | non-Tergenang, \(t^{\min}_{i,s} = T_{\text{pen}}\) (tidak mencapai TES mana pun) |
| Jauh | *remote* | non-Tergenang, terhubung, \(t^{\min}_{i,s} > T_{\text{evak}}\) |
| Terjangkau | — | \(t^{\min}_{i,s} \le T_{\text{evak}}\) |

**Beda dengan status TAS "TES terdekat tidak terjangkau".** Kategori akses **Terputus** menilai semua
TES valid (\(t^{\min} = T_{\text{pen}}\): tidak ada kategori TES yang dapat dicapai). Status TAS
"TES terdekat tidak terjangkau" hanya menilai satu TES, yaitu TES terdekat secara garis lurus \(e(i)\).
Karena itu setiap grid Terputus pasti juga "TES terdekat tidak terjangkau", tetapi tidak sebaliknya:
sebuah grid bisa gagal mencapai TES terdekatnya, tetapi masih mencapai TES lain lewat jaringan. Di
Baseline, jumlahnya 111 (Terputus) dan 168 (TES terdekat tidak terjangkau) (CATATAN P4-10).

Dilaporkan untuk \(T_{\text{evak}}\) = 30 menit (utama) serta 20 dan 40 menit (sensitivitas):
jumlah dan persentase per level, peta untuk Baseline, Sedang, dan Tinggi, dan matriks transisi kategori
akses 4 × 4 untuk empat pasangan level (pada 30 menit). Konstanta \(T_{\text{evak}}\) sama dengan
ambang isolasi REDCAP dan syarat \(T^{\text{aktual}}\) TAS (`EVAC_TIME_MIN`; nilai sensitivitas dari
`EVAC_TIME_SENS`).

## 11c. Atribusi pengaruh banjir pada TAS (Putaran 6)

Untuk setiap TAS pada level \(s \in\) {Rendah, Sedang, Tinggi}, dengan \(e_s(i)\) = TES terdekat secara
Euclidean (ID TES = kategori + indeks baris layer TES) dan \(T^{\text{aktual}}_{i,s}\) seperti §11.
Aturan ditetapkan peneliti sebelum hasil v6 terlihat. **TES sama** ⇔ \(e_s(i) = e_{\text{Baseline}}(i)\).

| Kelompok | Syarat |
|---|---|
| dipicu banjir | bukan TAS di Baseline, TES sama, dan \(T^{\text{aktual}}_{i,\text{Baseline}} <\) 30 menit |
| diperparah banjir | TAS di Baseline, TES sama, dan \(T^{\text{aktual}}_{i,s} - T^{\text{aktual}}_{i,\text{Baseline}} > 1\) menit |
| tidak berubah | TAS di Baseline, TES sama, dan \(\lvert T^{\text{aktual}}_{i,s} - T^{\text{aktual}}_{i,\text{Baseline}}\rvert \le 1\) menit |
| lainnya | selain itu; alasan dicatat (TES terdekat berubah; T_aktual turun; TES tidak terjangkau di Baseline; waktu Baseline ≥ 30 menit) |

Karena TES sama, "waktu Baseline ke TES itu" = \(T^{\text{aktual}}_{i,\text{Baseline}}\). Untuk kelompok
dipicu dan diperparah disimpan: waktu Baseline, waktu level, selisihnya, serta jumlah dan total panjang segmen
jalan yang **ditutup pada level itu dan dilalui rute Baseline** grid ke TES yang sama. Rute direkonstruksi
dengan snapping ke ruas yang sama (`thesis.tas_routes`). Sisi pecahan dipetakan ke segmen induknya,
termasuk segmen tempat ruas snapping mendarat.

Yang dilaporkan per level (T11f): jumlah dan persentase tiap kelompok terhadap TAS level itu, median waktu
Baseline kelompok dipicu, median tambahan waktu kelompok dipicu dan diperparah, serta peta atribusi untuk
Sedang dan Tinggi. Ambang 1 menit ditetapkan peneliti (§16).

## 11d. Validasi manual TAS dan kode penyebab (Putaran 6)

Lembar `output_bab4/validasi/validasi_TAS_v6.xlsx` (satu baris per grid TAS per level) memakai kode
penyebab:

| Kode | Penyebab | Valid |
|---|---|---|
| A | Sungai/waduk | Y |
| B | Kawasan tertutup/bandara | Y |
| C | Topografi perbukitan | Y |
| D | Jaringan jalan memang jarang | Y |
| E | Jaringan OSM tidak lengkap | T |
| F | Kesalahan snapping | T |
| G | Penutupan ruas akibat banjir | Y |
| H | TES lebih dekat tidak tercatat | T |
| I | Belum terjelaskan | cek |

Y = TAS nyata, T = artefak data/metode. Isian awal otomatis mengikuti prioritas yang ditetapkan peneliti:

- **(a) Baseline:** kode dari teks lembar v5 lewat aturan kata kunci, bila grid juga TAS di v5 dengan TES
  sama dan \(\lvert\Delta T^{\text{aktual}}\rvert \le\) 1 menit. Status "perlu konfirmasi peneliti".
  Teks berkode F (snapping) tidak dibawa bila grid masih TAS di v6.
- **(b) Dipicu banjir:** G, status otomatis.
- **(c) Diperparah banjir:** kode Baseline + G.
- **(d) Tidak berubah:** kode Baseline.
- **(e) Selain itu:** kosong, status "perlu divalidasi".

Grid yang perlu divalidasi/dikonfirmasi dikelompokkan menjadi hotspot (DBSCAN 350 m). Rekap
(`scripts/rekap_validasi_TAS.py`) menyajikan per level jumlah per kode dan Valid, atribusi × kode, per
hotspot, serta tabel Bab IV: TAS struktural (A/B/C/D), TAS akibat banjir (G), dan artefak data/metode (E/F/H).
Rincian keputusan implementasi: CATATAN P6-4.

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

## 13. Perbandingan algoritma (Baseline, K = 2, 3, dan 4)

Data: baris Baseline dari data gabungan (semua grid; ruang PCA dan praproses yang sama). Perbandingan
dijalankan untuk **K = 2, 3, dan 4**. Algoritma fuzzy memakai \(m = 1{,}7\) yang sama, 10 inisialisasi
(seed 42–51, \(J\) terkecil), dan aturan penomoran §10:

- **FCM**: SDWFCM dengan \(\alpha = 0\) (\(m = 1{,}7\)).
- **SFCM**: \(m = 1{,}7\) (sama dengan FCM dan SDWFCM; pada v2 \(m = 2\)), \(\alpha = 0{,}5\). \(d^s_{ik}\) = (rata-rata \(d^a\) tetangga rook) ×
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
ukuran klaster terbesar (%), dan waktu per inisialisasi. Untuk algoritma fuzzy juga dilaporkan
koefisien partisi \(\mathrm{PC} = \frac1N \sum_i \sum_k u_{ik}^2\) dan entropi partisi
\(\mathrm{PE} = -\frac1N \sum_i \sum_k u_{ik} \ln u_{ik}\) dari keanggotaan akhir.

Ketetanggaan rook (`build_weights`): rook (fallback queen), grid tanpa tetangga diberi 2 tetangga
terdekat, dan komponen terputus disambungkan melalui pasangan grid terdekat.

## 14. Simulasi blokir jalan di dashboard (bukan hasil skripsi)

Dashboard menghitung ulang aksesibilitas level terpilih dengan ruas yang diblokir pengguna, lalu
menerapkan praproses data gabungan (parameter tersimpan). Keanggotaan dihitung terhadap **pusat
klaster final yang tetap**: iterasi \(U\) dengan \(d^t\) pada §8 dan \(W\) KNN-Gaussian level
tersebut, sedangkan pusat tidak diperbarui. Model tidak di-fit ulang, sehingga nomor klaster tetap
bermakna sama. Dashboard menampilkan K utama (`pengaturan_hasil.json`) secara bawaan dan menyediakan
pilihan untuk beralih ke K lainnya.

## 15. Reproduksibilitas

- Seed: SDWFCM/FCM/SFCM 42–51, subsampel \(20240 + b\), Dunn 42–46, Silhouette 42, permutasi Moran 42.
  Satu thread BLAS/OpenMP.
- Hasil dianggap identik bila fingerprint `thesis_results.json` (tanpa field waktu dan `meta.git`)
  dan SHA-256 isi CSV grid dan data gabungan sama; lihat `scripts/cek_reproduksi.py` dan README.

## 16. Alasan operasional parameter yang ditetapkan peneliti

Parameter berikut belum punya rujukan (`docs/RUJUKAN_PARAMETER.md`: "ditetapkan peneliti"). Alasannya
bersifat operasional:

- **T_ideal ≤ 5 menit (garis lurus ≤ 400 m).** Membatasi TAS pada grid yang TES-nya secara kasat mata
  dekat: empat lebar grid 100 m, atau sekitar satu blok permukiman. Hanya pada grid seperti ini
  "rasa aman" karena kedekatan dapat menyesatkan.
- **DI_t ≥ 2.** Jalur jaringan minimal dua kali jarak garis lurus, sehingga penyimpangan rute jelas
  lebih besar dari variasi normal jaringan jalan. Pada Baseline v3, median DI grid Non-TAS ± 1,5.
- **Snapping ≤ 300 m.** Tiga lebar grid. Menghubungkan centroid di area bangunan jarang ke jalan
  terdekat tanpa menghubungkan grid yang jelas terpisah dari jaringan; grid di luar batas ini menjadi
  Terputus.
- **Toleransi 1 menit pada atribusi banjir (Putaran 6).** "Diperparah" bila T_aktual naik > 1 menit, "tidak
  berubah" bila perubahan ≤ 1 menit. Toleransi operasional: menyerap perbedaan numerik kecil (pembulatan,
  perubahan titik proyeksi snapping saat ruas di dekat grid ditutup) yang tidak bermakna bagi evakuasi,
  sehingga hanya kenaikan yang jelas dihitung sebagai pengaruh banjir.
- **Hotspot validasi 350 m (Putaran 6).** DBSCAN 350 m (± 3,5 lebar grid) mengelompokkan grid TAS yang
  berdekatan agar satu lokasi cukup diperiksa sekali pada citra satelit. Hanya alat bantu validasi, tidak
  memengaruhi hasil.
- **Jarak minimum 50 m pada T_ideal dan T_aktual.** Setengah lebar grid. Mencegah penyebut DI mendekati
  nol ketika TES berada di dalam atau sangat dekat centroid grid. Dipasang pada kedua jarak agar
  T_aktual ≥ T_ideal (CATATAN P2-B2).

## 17. Keterbatasan

- **Standar waktu evakuasi.** Batas 30 menit (dan sensitivitas 20/40 menit) berasal dari praktik
  Korea (Park dkk., 2020) dan Tiongkok (Li dkk., 2026). Belum ditemukan standar waktu evakuasi banjir
  nasional yang setara di Indonesia. Rujukan Indonesia yang ada (Palabuhanratu, Padang, pedoman BNPB
  2013) berkonteks tsunami.
- **Kecepatan berjalan seragam** (80 m/menit), tanpa pengaruh lereng dan tanpa perbedaan kelompok
  rentan. Park dkk. (2020) memakai koreksi Naismith–Langmuir untuk lereng. Keterbatasan ini relevan
  untuk wilayah Perbukitan Menoreh.
- **Penutupan ruas berbasis kelas bahaya InaRisk, bukan kedalaman genangan.** Li dkk. (2026) memakai
  ambang kedalaman 0,3 m. Tidak ada reduksi kecepatan parsial pada ruas yang tergenang dangkal.
- **Kapasitas TES dan jumlah penduduk tidak diperhitungkan** (Li dkk., 2026, memakai G2SFCA). Tidak
  ada validasi terhadap lokasi banjir historis.
- **TES diasumsikan beroperasi penuh selama banjir**, kecuali yang tidak valid menurut kelas bahaya
  dan radius 50 m dari grid Tergenang.

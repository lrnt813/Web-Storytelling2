# Rujukan parameter

Status verifikasi:
- **terverifikasi peneliti**: peneliti sudah memeriksa isi rujukan pada halaman yang disebut;
- **perlu verifikasi peneliti**: rujukan diberikan, tetapi isinya belum diperiksa atau statusnya belum
  jelas;
- **ditetapkan peneliti**: tidak ada rujukan; alasan operasional ditulis di `docs/METODOLOGI.md`
  (§ Alasan operasional parameter yang ditetapkan peneliti).

Rujukan di bawah dicatat persis seperti yang diberikan peneliti (Putaran 4). Tidak ada rujukan yang
ditambahkan sendiri. Status "terverifikasi peneliti" hanya diberikan bila peneliti menyatakannya; saat
ini belum ada parameter yang dinyatakan demikian.

| Parameter | Nilai | Konstanta di kode | Rujukan | Halaman | Status |
|---|---|---|---|---|---|
| Kecepatan berjalan | 80 m/menit (≈ 4,8 km/jam; 1,33 m/detik) | `Cfg.walking_speed_m_per_min` | Li, Ba, Huang, & Shi (2026), *Geo-spatial Information Science* 29(4), 2910–2928, doi:10.1080/10095020.2025.2597523 (kecepatan berjalan normal 5 km/jam sebagai asumsi standar); Bohannon (1997), *Age and Ageing* 26, 15–19 (kisaran kecepatan nyaman) | Li dkk. hlm. 2915 | **perlu verifikasi peneliti** (Bohannon: perlu verifikasi; nilai 80 m/menit sedikit di bawah 5 km/jam = 83,3 m/menit) |
| Batas waktu evakuasi | 30 menit | `engine.EVAC_TIME_MIN` | Li dkk. (2026): ambang tangkapan d0 = 30 menit mengikuti pedoman resmi Pemerintah Provinsi Guangdong tentang area layanan shelter darurat; Park, Lee, & Kim (2020), *ISPRS IJGI* 9(4), 207, doi:10.3390/ijgi9040207: rekomendasi evakuasi darurat 30 menit dari otoritas kebencanaan Korea; Chelariu, Iațu, & Minea (2022), *Water* 14(19), 3074, doi:10.3390/w14193074 | Li dkk. hlm. 2915; Park dkk. hlm. 5 | **perlu verifikasi peneliti** (Chelariu dkk.: belum jelas apakah 30 menit ambang atau hanya interval pelaporan) |
| Nilai sensitivitas batas waktu | 20 dan 40 menit | `engine.EVAC_TIME_SENS` | Li dkk. (2026): sensitivitas d0 = 20, 30, 40 menit | hlm. 2920 | **perlu verifikasi peneliti** |
| Kategori akses (Tergenang/Terputus/Jauh/Terjangkau) | padanan *flooded / isolated / remote* | `thesis.AKSES_STATUS` | Li dkk. (2026): kategori komunitas tanpa akses | hlm. 2919 | **perlu verifikasi peneliti** |
| T_ideal maksimum pada aturan TAS | ≤ 5 menit (garis lurus ≤ 400 m) | `thesis.TAS_T_IDEAL_MAX` | — | — | **ditetapkan peneliti** |
| Detour Index minimum pada aturan TAS | DI_t ≥ 2 | `thesis.TAS_DI_ABSOLUTE` | — | — | **ditetapkan peneliti** |
| T_aktual minimum pada aturan TAS | ≥ 30 menit (= batas waktu evakuasi) | `thesis.TAS_T_AKTUAL_MIN = EVAC_TIME_MIN` | sama dengan batas waktu evakuasi | — | **perlu verifikasi peneliti** |
| Batas snapping ke jaringan jalan | 300 m | `engine.SNAP_MAX_M` | — | — | **ditetapkan peneliti** |
| Jarak minimum T_ideal dan T_aktual | 50 m | `thesis.TAS_MIN_EUCLID_M` | — | — | **ditetapkan peneliti** |
| Ambang isolasi REDCAP | 30 menit (= batas waktu evakuasi) | `Cfg.isolation_time_threshold = EVAC_TIME_MIN` | sama dengan batas waktu evakuasi | — | **perlu verifikasi peneliti** |

## Konteks praktik Indonesia (bukan dasar ambang banjir)

Dicatat sebagai konteks, tidak dipakai sebagai dasar parameter:

- studi keterjangkauan TES Palabuhanratu (repositori IPB; 30 menit berjalan kaki, konteks tsunami);
- Di Mauro dkk. (2013), *Natural Hazards* 68(2), 373–404 (Padang; waktu tiba tsunami ± 30 menit);
- pedoman BNPB 2013 tentang perencanaan TES tsunami (**belum diperiksa** apakah memuat standar waktu
  tempuh).

## Parameter yang masih perlu tindakan peneliti

- **perlu verifikasi peneliti:** kecepatan berjalan (termasuk Bohannon 1997), batas waktu evakuasi
  30 menit (termasuk status Chelariu dkk. 2022), sensitivitas 20/40 menit, padanan kategori akses,
  T_aktual ≥ 30 menit, ambang isolasi REDCAP 30 menit.
- **ditetapkan peneliti (belum ada rujukan):** T_ideal ≤ 5 menit, DI_t ≥ 2, snapping 300 m, jarak
  minimum 50 m.

# Deploy ke Hugging Face Spaces (versi lengkap)

Dashboard dijalankan sebagai **Docker Space** di Hugging Face (gratis: 2 vCPU, 16 GB RAM).
Kode tetap disimpan di GitHub; workflow GitHub Actions mengirim salinan ringkas
(kode + ±130 MB data yang dipakai server) ke Space.

## Persiapan (sekali saja)

1. **Buat akun** di <https://huggingface.co/join>.
2. **Buat Space**: <https://huggingface.co/new-space>
   - *Space name*: mis. `dashboard-tes-banjir`
   - *SDK*: **Docker** → template **Blank**
   - *Hardware*: **CPU basic (free)**
   - *Visibility*: Public (atau Private bila hanya untuk penguji)
3. **Buat token**: <https://huggingface.co/settings/tokens> → *Create new token* →
   tipe **Write** → salin token (diawali `hf_…`).
4. **Isi pengaturan di GitHub** (repo → *Settings* → *Secrets and variables* → *Actions*):
   - tab **Secrets** → *New repository secret* → nama `HF_TOKEN`, isi token dari langkah 3
   - tab **Variables** → *New repository variable* → nama `HF_SPACE`,
     isi `<username-hf>/<nama-space>`, mis. `lrnt813/dashboard-tes-banjir`

## Deploy / memperbarui

1. Push perubahan ke GitHub seperti biasa.
2. GitHub → tab **Actions** → **Deploy ke Hugging Face Spaces** → **Run workflow**.
3. Hugging Face otomatis membangun image (±5–10 menit; lihat tab *Logs* di Space).
4. Dashboard tersedia di `https://<username-hf>-<nama-space>.hf.space`
   (halaman Space di `https://huggingface.co/spaces/<username-hf>/<nama-space>`).

## Catatan

- **Tidur saat tidak dipakai**: Space gratis berhenti setelah ±48 jam tanpa pengunjung;
  pembukaan berikutnya menunggu 1–2 menit hingga server menyala kembali.
- **Kuota LFS GitHub**: setiap deploy mengunduh ±130 MB data dari penyimpanan LFS GitHub,
  karena itu workflow hanya berjalan saat dijalankan manual.
- **Hasil penelitian terkunci**: server membaca `data/thesis_results.json` dan
  `data/thesis_grid_results.csv.gz`; tidak ada analisis ulang di server.
- **Unduhan & GPS**: gunakan alamat langsung `*.hf.space` (bukan halaman Space yang
  memuat dashboard dalam bingkai) agar unduhan Excel/PNG dan tombol GPS berfungsi penuh.
- **Beban server**: simulasi blokir jalan memakan ±15 detik CPU per permintaan dan
  dijalankan bergiliran; cocok untuk demonstrasi, bukan untuk ribuan pengguna sekaligus.

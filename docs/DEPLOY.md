# Membagikan Dashboard secara Online (Cloudflare Tunnel)

Dashboard berjalan di laptop sendiri, lalu **Cloudflare Tunnel** memberinya alamat publik
`https://…​.trycloudflare.com` yang dapat dibuka siapa saja. Gratis, tanpa akun, tanpa kartu kredit.
Semua fitur tersedia (rute evakuasi, simulasi blokir jalan, pencarian alamat, unduhan).

## Cara menjalankan

- **Klik dua kali** `Jalankan Dashboard Publik.bat`, atau jalankan
  `python start_dashboard.py --publik`
- Tunggu ±20–30 detik. Alamat publik tampil di jendela, dibuka otomatis di browser,
  dan disimpan di `scratch/alamat_publik.txt` untuk disalin/dibagikan.
- **Menghentikan:** tekan `Ctrl+C` (atau tutup jendela). Alamat publik langsung tidak aktif.

Untuk pemakaian di laptop saja (tanpa alamat publik): `Jalankan Dashboard.bat`
atau `python start_dashboard.py`.

Program `cloudflared` diunduh otomatis dari rilis resmi Cloudflare saat pertama kali
dipakai (checksum SHA-256 diverifikasi) dan disimpan di `tools/` (tidak di-commit).

## Yang perlu diperhatikan

- **Alamat berubah** setiap kali dijalankan ulang → bagikan alamat yang baru.
- **Laptop harus menyala & terhubung internet.** Atur *Power & sleep* agar laptop tidak
  tidur (sleep) selama dashboard dibagikan, dan colokkan charger.
- **Kecepatan** mengikuti internet laptop (terutama kecepatan *upload*). Data sudah
  dikompresi: pembukaan awal ±3 MB, pergantian level ±1 MB.
- **Jumlah pengguna:** cocok untuk demonstrasi, sidang, atau beberapa penguji sekaligus.
  Simulasi blokir jalan memakan ±15 detik CPU per permintaan dan dijalankan bergiliran.
- **Keamanan:** siapa pun yang tahu alamatnya dapat membuka dashboard (hanya-baca; hasil
  penelitian terkunci dan tidak dapat diubah dari browser). Hentikan tunnel bila tidak dipakai.
- Tunnel cepat (*quick tunnel*) ini ditujukan untuk pengujian/demonstrasi; untuk layanan
  permanen dengan alamat tetap diperlukan akun Cloudflare dan domain sendiri.

## Hosting permanen gratis: Hugging Face Spaces (+ Netlify opsional)

Netlify hanya bisa menyajikan berkas statis (folder `frontend/`). Server Python (FastAPI + GeoPandas/SciPy,
RAM ± 1,5 GB) tidak bisa berjalan di Netlify, sehingga bila hanya Netlify yang dipakai, halaman tampil tetapi
semua data (`/api/...`) gagal dimuat. Solusinya: seluruh dashboard dijalankan di **Hugging Face Spaces**
(gratis, tanpa kartu kredit, ± 16 GB RAM), dan Netlify hanya opsional sebagai alamat kedua.

### A. Membuat Space (sekali)

1. Daftar/masuk di https://huggingface.co.
2. Buat token: *Settings → Access Tokens → Create new token* → jenis **Write** → salin token (`hf_…`).
3. Di GitHub (repo ini): *Settings → Secrets and variables → Actions*:
   - tab **Secrets** → *New repository secret*: nama `HF_TOKEN`, isi token tadi;
   - tab **Variables** → *New repository variable*: nama `HF_SPACE`, isi `NAMA_PENGGUNA_HF/dashboard-tes-kulonprogo`.
4. Di GitHub tab **Actions** → *Sinkronkan ke Hugging Face Space* → **Run workflow**. Space dibuat otomatis
   dan berkas diunggah (± 164 MB; hanya berkas yang dibutuhkan server, lihat `scripts/deploy_hf_space.py`).
5. Buka `https://huggingface.co/spaces/NAMA_PENGGUNA_HF/dashboard-tes-kulonprogo` dan tunggu build selesai
   (± 10–15 menit pertama kali; status **Running**). Alamat dashboard:
   `https://nama_pengguna_hf-dashboard-tes-kulonprogo.hf.space` (huruf kecil; garis bawah menjadi tanda hubung).

Setelah itu setiap push ke `main` yang mengubah backend, frontend, data, atau `Dockerfile` otomatis memperbarui
Space. Tanpa GitHub Actions, unggahan juga bisa dari laptop:

```
set HF_TOKEN=hf_xxx
python -m scripts.deploy_hf_space --space NAMA_PENGGUNA_HF/dashboard-tes-kulonprogo
```

Catatan: Space gratis "tidur" bila ± 48 jam tidak dibuka; pembukaan berikutnya memerlukan ± 1–2 menit untuk
bangun dan memuat data. Space bersifat publik (hanya-baca; hasil penelitian tidak dapat diubah dari browser).

### B. Netlify (opsional)

1. Di `netlify.toml`, ganti `NAMA-PENGGUNA-HF-dashboard-tes-kulonprogo.hf.space` dengan alamat Space dari
   langkah A.5, lalu commit dan push.
2. Di Netlify: *Add new site → Import from GitHub* → pilih repo ini. Pengaturan build dibaca dari
   `netlify.toml` (*Publish directory* = `frontend`, tanpa build command).
3. Netlify menyajikan halaman dan meneruskan semua permintaan `/api/*` ke Space. Space harus berstatus
   **Running**; bila Space sedang tidur, permintaan pertama dapat gagal sampai Space bangun.

## Alternatif hosting permanen

`Dockerfile` dan `requirements.txt` sudah tersedia, sehingga dashboard dapat dipasang di
layanan berbasis container (mis. Google Cloud Run, Azure for Students) atau server Linux
(mis. Oracle Cloud Always Free). Server membutuhkan RAM ±1,5 GB; layanan gratis dengan
RAM 512 MB tidak mencukupi.

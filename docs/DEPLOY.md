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

## Alternatif hosting permanen

`Dockerfile` dan `requirements.txt` sudah tersedia, sehingga dashboard dapat dipasang di
layanan berbasis container (mis. Google Cloud Run, Azure for Students) atau server Linux
(mis. Oracle Cloud Always Free). Server membutuhkan RAM ±1,5 GB; layanan gratis dengan
RAM 512 MB tidak mencukupi.

# Alur Kerja Repositori

Repositori ini adalah **satu-satunya versi resmi** kode dan hasil penelitian. Arah kebenaran:
**kode → hasil → skripsi**. Angka di naskah mengikuti hasil. Kode tidak boleh disetel agar
cocok dengan angka tertentu.

## Aturan tetap

1. **Commit dan push setiap sesi kerja.** Jangan tinggalkan perubahan kode tanpa commit.
   Pesan commit berbahasa Indonesia dan menjelaskan *apa* serta *mengapa*.
2. **Jangan pernah mengedit manual isi `data/locked/`.** Folder ini hanya boleh diisi oleh
   `python -m scripts.kunci_hasil`. Setiap berkas punya SHA-256 di `LOCK.json`, dan
   `scripts/export_bab4.py` menolak berjalan jika hash tidak cocok.
3. **Semua angka skripsi berasal dari `output_bab4/`.** Folder ini dibangun ulang dengan
   `python -m scripts.export_bab4` dari `data/locked/` saja. Jangan menyalin angka dari
   dashboard, log, atau draft lama.
4. **Temuan yang janggal dicatat di `docs/CATATAN_TEMUAN.md`.** Jangan diperbaiki diam-diam.
   Perubahan metode harus diputuskan bersama pembimbing, lalu dikerjakan lewat alur di bawah.
5. `docs/angka_draft_lama.json` hanya arsip pembanding. Berkas ini tidak boleh diimpor oleh
   backend atau pipeline.

## Mengubah metode lalu memperbarui hasil

```bash
git switch -c <branch-perubahan>
# ... ubah kode, tambahkan/ubah uji ...
python -m pytest -q                                   # semua uji harus lulus
git commit -am "Ubah ...: alasan"                     # 1. commit kode
python -m scripts.thesis_analysis --force             # 2. jalankan (±1,7 jam; jangan biarkan laptop sleep)
python -m scripts.kunci_hasil                         # 3. kunci (ditolak bila kode belum di-commit)
python -m scripts.export_bab4                         # 4. bangun tabel Bab IV
git add data/locked output_bab4 && git commit -m "Hasil terkunci: ..."   # 5. commit hasil
git tag hasil-skripsi-vN && git push --follow-tags     # 6. tag versi hasil
```

Untuk memeriksa determinisme, jalankan analisis dua kali dan bandingkan
`results_fingerprint` (lihat README). Untuk memeriksa bahwa hasil terkunci masih dapat
direproduksi di lingkungan saat ini: `python -m scripts.cek_reproduksi`.

## Lingkungan

Versi Python ada di `.python-version` dan versi pustaka dipin di `requirements.txt`. Versi yang
benar-benar dipakai saat penguncian juga tercatat di `data/locked/LOCK.json`. Hasil numerik
dapat berbeda di versi pustaka lain. Gunakan `cek_reproduksi` untuk memastikan.

# Struktur Proyek

```text
Web-Storytelling2/
  start_dashboard.py      Peluncur: memeriksa hasil analisis, menjalankan backend, membuka browser
  main.py                 Shim kompatibilitas (`python main.py` → backend.main)
  backend/
    main.py               Aplikasi FastAPI (API level banjir, simulasi, rute, wilayah, geocoding)
    thesis.py             Metodologi skripsi Bab III–IV (pra-pemrosesan, SDWFCM, metrik, transisi, TAS)
    engine.py             Modul komputasi dasar (Lampiran 1): data, graf jalan, jarak, algoritma klaster
    pseudo_safety.py      Fungsi pelabelan ulang klaster (Lampiran 2), dipakai engine.py
    config.py, state.py, schemas.py
  scripts/
    thesis_analysis.py    Analisis offline Bab IV → data/thesis_results.json & thesis_grid_results.csv.gz
    export_geometry.py    Ekspor geometri grid statis untuk frontend
    export_roads.py       Ekspor jaringan jalan
  frontend/
    index.html, css/styles.css
    js/config.js          Konstanta, warna, level, helper umum
    js/map-layers.js      Peta dasar, grid, TES, jalan, level & tampilan, blokir jalan, pembanding level
    js/routing.js         Popup detail grid & rute evakuasi
    js/legend.js          Legenda per tampilan
    js/boundaries.js      Batas kabupaten/kapanewon/kalurahan
    js/regions.js         Ringkasan & peringkat prioritas wilayah
    js/search.js          Pencarian wilayah & alamat
    js/results.js         Panel "Hasil Penelitian" (Tabel 8–16, grafik)
    js/export.js          Unduh tabel (Excel/CSV) & grafik (PNG)
    js/bootstrap.js       Inisialisasi
  data/
    *.gpkg                Data spasial masukan (grid, jalan, TES, batas administrasi BIG)
    thesis_results.json, thesis_grid_results.csv.gz   Hasil analisis (dibaca dashboard)
    locked/               Salinan hasil terkunci + LOCK.json (checksum)
  scratch/                Cache & log sementara (tidak di-commit)
  Dockerfile, requirements.txt, .github/workflows/deploy-huggingface.yml
                          Deploy ke Hugging Face Spaces (lihat docs/DEPLOY.md)
```

Hasil analisis dikunci. Untuk menghitung ulang: `python -m scripts.thesis_analysis --force`.

"""Unggahan ke Hugging Face Space hanya memuat berkas yang dibutuhkan server dashboard."""
from scripts.deploy_hf_space import README_SPACE, daftar_berkas


def test_berkas_server_lengkap_dan_arsip_tidak_ikut():
    b = set(daftar_berkas())
    for wajib in ("Dockerfile", "requirements.txt", "pengaturan_hasil.json", "backend/main.py", "frontend/index.html",
                  "frontend/static_grid_kulonprogo.geojson", "data/Kulonprogo_Ready4.gpkg", "data/Kulonprogo_Jalan.gpkg",
                  "data/Kulonprogo_Banjir.tif", "data/thesis_results.json", "data/thesis_grid_results.csv.gz",
                  "data/locked/LOCK.json", "scripts/thesis_analysis.py"):
        assert wajib in b, wajib
    assert not any(p.startswith(("data/hasil_clustering", "data/locked/arsip_", "output_bab4", "docs/", "tests/",
                                 "scratch/")) for p in b)
    assert not any("__pycache__" in p for p in b)


def test_readme_space_bermetadata_docker():
    assert README_SPACE.startswith("---\n") and "sdk: docker" in README_SPACE and "app_port: 7860" in README_SPACE

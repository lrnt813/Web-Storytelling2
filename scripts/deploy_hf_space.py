"""Unggah dashboard ke Hugging Face Space (Docker) — hanya berkas yang dibutuhkan server saat berjalan.

    set HF_TOKEN=hf_xxx                          (token Hugging Face dengan izin "write")
    python -m scripts.deploy_hf_space --space NAMA_PENGGUNA/dashboard-tes-kulonprogo
    python -m scripts.deploy_hf_space --space ... --cek     # hanya tampilkan daftar & ukuran berkas

Juga dijalankan otomatis oleh .github/workflows/sync-huggingface.yml setiap push ke main.

Yang diunggah (± 145 MB): Dockerfile, requirements.txt, pengaturan_hasil.json, backend/, frontend/, scripts/,
GeoPackage dan raster di data/, berkas hasil kerja data/thesis_*, serta hasil terkunci data/locked/ tanpa arsip.
Yang TIDAK diunggah: data/hasil_clustering (316 MB, tidak dipakai server), data/locked/arsip_*, output_bab4/,
docs/, tests/, scratch/. README Space (metadata `sdk: docker`, `app_port: 7860`) dibuat oleh skrip ini, jadi
README repo GitHub tidak berubah. Space dibuat otomatis bila belum ada. Unggahan mengganti seluruh isi Space
(berkas yang tidak lagi ada dihapus). Hasil penelitian tidak diubah.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BERKAS = ["Dockerfile", ".dockerignore", "requirements.txt", "pengaturan_hasil.json"]
FOLDER = ["backend", "frontend", "scripts"]
DATA_POLA = ["*.gpkg", "*.tif", "thesis_results.json", "thesis_grid_results.csv.gz", "thesis_pooled_results.csv.gz",
             "Penduduk_Desa_KulonProgo.csv"]
LOCKED = ["LOCK.json", "thesis_results.json", "thesis_grid_results.csv.gz", "thesis_pooled_results.csv.gz"]
ABAIKAN = shutil.ignore_patterns("__pycache__", "*.pyc")

README_SPACE = """---
title: Aksesibilitas TES Banjir Kulon Progo
emoji: 🗺️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Dashboard tipologi aksesibilitas TES banjir (SDWFCM)
---

Dashboard skripsi: pemetaan aksesibilitas spasial bangunan publik sebagai Tempat Evakuasi Sementara (TES)
banjir di Kabupaten Kulon Progo (SDWFCM, grid 100 × 100 m). Kode sumber dan dokumentasi lengkap ada di
repositori GitHub; Space ini disinkronkan otomatis dan hanya memuat berkas yang dibutuhkan server.
"""


def daftar_berkas(root: Path = ROOT) -> list:
    """Path relatif (terhadap root) semua berkas yang diunggah ke Space."""
    out = [root / f for f in BERKAS if (root / f).exists()]
    for d in FOLDER:
        out += [p for p in (root / d).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    for pola in DATA_POLA:
        out += sorted((root / "data").glob(pola))
    out += [root / "data" / "locked" / f for f in LOCKED if (root / "data" / "locked" / f).exists()]
    return sorted({p.relative_to(root).as_posix() for p in out})


def siapkan_folder(tujuan: Path, root: Path = ROOT) -> list:
    """Salin berkas yang diunggah ke folder `tujuan` dan tulis README Space. Returns daftar berkas."""
    berkas = daftar_berkas(root)
    for rel in berkas:
        dst = tujuan / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    (tujuan / "README.md").write_text(README_SPACE, encoding="utf-8")
    return berkas + ["README.md"]


def normalisasi_space(nilai: str) -> str:
    """'https://huggingface.co/spaces/user/nama', 'spaces/user/nama', ' user/nama ' → 'user/nama'.
    Error berbahasa Indonesia bila formatnya tidak bisa dipakai."""
    import re
    v = (nilai or "").strip().strip("/")
    v = re.sub(r"^(https?://)?(www\.)?huggingface\.co/", "", v)
    v = re.sub(r"^spaces/", "", v)
    if v.endswith(".hf.space") or "hf.space" in v:
        raise SystemExit(f"HF_SPACE berisi alamat dashboard ({nilai!r}). Isi dengan NAMA_PENGGUNA_HF/nama-space, "
                         "misalnya budi123/dashboard-tes-kulonprogo.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*", v):
        raise SystemExit(f"Format HF_SPACE tidak valid: {nilai!r}. Isi dengan NAMA_PENGGUNA_HF/nama-space "
                         "(satu tanda '/', tanpa spasi dan tanpa https://).")
    return v


def _cek_lfs(root: Path, berkas: list):
    """Berkas Git LFS yang belum diunduh hanya berisi pointer teks kecil; hentikan agar Space tidak rusak."""
    for rel in berkas:
        p = root / rel
        if p.suffix in (".gpkg", ".tif") and p.stat().st_size < 1024 \
                and p.read_bytes()[:40].startswith(b"version https://git-lfs"):
            raise SystemExit(f"{rel} masih berupa pointer Git LFS. Jalankan `git lfs pull` terlebih dahulu.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Unggah dashboard ke Hugging Face Space (Docker)")
    ap.add_argument("--space", default=os.environ.get("HF_SPACE"), help="NAMA_PENGGUNA/nama-space")
    ap.add_argument("--cek", action="store_true", help="hanya tampilkan daftar berkas dan ukurannya")
    args = ap.parse_args(argv)
    berkas = daftar_berkas()
    total = sum((ROOT / b).stat().st_size for b in berkas)
    print(f"{len(berkas)} berkas, {total / 1e6:.1f} MB")
    if args.cek:
        print("\n".join(berkas))
        return 0
    if not args.space:
        raise SystemExit("Isi --space NAMA_PENGGUNA/nama-space (atau variabel HF_SPACE).")
    args.space = normalisasi_space(args.space)
    token = (os.environ.get("HF_TOKEN") or "").strip()
    if not token:
        raise SystemExit("Variabel lingkungan HF_TOKEN (token Hugging Face dengan izin write) belum diisi.")
    _cek_lfs(ROOT, berkas)
    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError
    api = HfApi(token=token)
    try:
        info = api.whoami()
    except HfHubHTTPError as e:
        raise SystemExit(f"Token HF_TOKEN ditolak Hugging Face ({e}). Buat token baru jenis 'Write' lalu perbarui "
                         "secret HF_TOKEN di GitHub.")
    pemilik = info.get("name")
    organisasi = [o.get("name") for o in info.get("orgs", [])]
    namespace = args.space.split("/", 1)[0]
    print(f"Token milik: {pemilik}; Space tujuan: {args.space}")
    if namespace not in [pemilik] + organisasi:
        raise SystemExit(f"Nama pengguna di HF_SPACE ({namespace!r}) bukan pemilik token ({pemilik!r}). Ubah variable "
                         f"HF_SPACE menjadi {pemilik}/{args.space.split('/', 1)[1]}.")
    try:
        api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            siapkan_folder(Path(tmp))
            api.upload_folder(folder_path=tmp, repo_id=args.space, repo_type="space", delete_patterns="*",
                              commit_message="Sinkronisasi dashboard dari GitHub")
    except HfHubHTTPError as e:
        kode = getattr(getattr(e, "response", None), "status_code", None)
        saran = (" Token kemungkinan hanya berizin baca: buat token jenis 'Write' (atau token fine-grained dengan izin "
                 "menulis repo/Space) lalu perbarui secret HF_TOKEN." if kode in (401, 403) else "")
        raise SystemExit(f"Hugging Face menolak unggahan (HTTP {kode}): {e}.{saran}")
    user, nama = args.space.split("/", 1)
    print(f"Selesai. Space: https://huggingface.co/spaces/{args.space}")
    print(f"Alamat dashboard (setelah build ± 10–15 menit): https://{user.lower()}-{nama.lower().replace('_', '-')}.hf.space")
    return 0


def _jalankan():
    """main() dengan pesan kesalahan yang juga ditulis sebagai anotasi GitHub Actions (terlihat di ringkasan run)."""
    try:
        return main()
    except SystemExit as e:
        if isinstance(e.code, str) and os.environ.get("GITHUB_ACTIONS"):
            print("::error title=Unggah ke Hugging Face gagal::" + e.code.replace("
", " "), flush=True)
        raise
    except Exception as e:                                        # kesalahan tak terduga
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=Unggah ke Hugging Face gagal::{type(e).__name__}: {e}".replace("
", " "), flush=True)
        raise


if __name__ == "__main__":
    sys.exit(_jalankan())

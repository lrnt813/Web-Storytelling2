import os
from pathlib import Path

from pyproj import Transformer

from .engine import Cfg


# backend/ lives one level below the project root.
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = os.environ.get("SDWFCM_DATA_DIR", str(BASE_DIR / "data"))

cfg = Cfg(base_dir=DATA_DIR)

wgs84_to_utm = Transformer.from_crs("EPSG:4326", cfg.target_crs, always_xy=True)
utm_to_wgs84 = Transformer.from_crs(cfg.target_crs, "EPSG:4326", always_xy=True)


PENGATURAN_HASIL = BASE_DIR / "pengaturan_hasil.json"


def k_utama_default() -> int:
    """K model utama (satu konfigurasi bersama export_bab4 dan dashboard)."""
    import json
    try:
        return int(json.loads(PENGATURAN_HASIL.read_text(encoding="utf-8"))["k_utama"])
    except (OSError, KeyError, ValueError):
        return 3


TERGENANG_LABEL = "Tergenang (di luar klasterisasi)"


def deskripsi_tipologi(k: int) -> dict:
    """Deskripsi tipologi per klaster (penyajian; pengaturan_hasil.json → deskripsi_tipologi). Klaster c
    (0 = terbaik) → teks deskripsi; kosong bila tidak diatur untuk K ini."""
    import json
    try:
        lst = json.loads(PENGATURAN_HASIL.read_text(encoding="utf-8")).get("deskripsi_tipologi", {}).get(str(k), [])
    except (OSError, ValueError):
        lst = []
    return {str(c): t for c, t in enumerate(lst)} if len(lst) == k else {}


def label_tipologi(c: int, k: int) -> str:
    """Label tampilan tipologi: "Tipologi c+1: deskripsi" (atau "Tipologi c+1" bila deskripsi tidak ada).
    c = k (state Tergenang) → TERGENANG_LABEL."""
    if int(c) == int(k) or int(c) < 0:
        return TERGENANG_LABEL
    desk = deskripsi_tipologi(k).get(str(int(c)))
    return f"Tipologi {int(c) + 1}: {desk}" if desk else f"Tipologi {int(c) + 1}"

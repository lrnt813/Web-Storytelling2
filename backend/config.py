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

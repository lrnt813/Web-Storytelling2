import geopandas as gpd
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine import Cfg

cfg = Cfg(base_dir=str(PROJECT_ROOT / "data"))
if os.path.exists(cfg.input_file):
    gdf = gpd.read_file(cfg.input_file)
    print(f"File: {cfg.input_file}")
    cols = [c for c in gdf.columns if "PSI_" in c]
    print(f"PSI Columns found: {cols}")
    for c in cols:
        print(f"{c} - Max: {gdf[c].max()}, Min: {gdf[c].min()}, Avg: {gdf[c].mean()}")
        print(f"Grids with {c} >= 0.5: {(gdf[c] >= 0.5).sum()}")
else:
    print(f"File not found: {cfg.input_file}")

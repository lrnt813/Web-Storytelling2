import asyncio
from typing import Dict, Optional

import geopandas as gpd
import pandas as pd


class AppState:
    gdf_base: Optional[gpd.GeoDataFrame] = None
    roads_raw: Optional[gpd.GeoDataFrame] = None
    tes_raw: Dict[str, gpd.GeoDataFrame] = {}
    is_ready: bool = False
    startup_error: Optional[str] = None

    # Hasil analisis skripsi (offline)
    thesis_results: dict = {}
    thesis_grid: Optional[pd.DataFrame] = None
    level_cache: Dict[tuple, dict] = {}     # (level, K) -> payload
    t_pen: Optional[float] = None

    graph_cache: Dict[tuple, tuple] = {}
    compute_lock: Optional[asyncio.Lock] = None
    roads_signature: str = "unknown"
    graph_cache_stats: Dict[str, int] = {
        "memory_hits": 0,
        "disk_hits": 0,
        "misses": 0,
        "writes": 0,
        "evictions": 0,
        "stale_disk_pruned": 0,
    }


state = AppState()

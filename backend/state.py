import asyncio
from typing import Dict, Optional

import geopandas as gpd
import numpy as np


class AppState:
    gdf_base: Optional[gpd.GeoDataFrame] = None
    roads_raw: Optional[gpd.GeoDataFrame] = None
    tes_raw: Dict[str, gpd.GeoDataFrame] = {}
    w_baseline = None
    nx_graph_base = None
    nx_node_list = None
    nx_kdtree = None
    is_ready: bool = False
    startup_error: Optional[str] = None

    graph_cache: Dict[tuple, tuple] = {}
    cluster_ranks: Dict[str, Dict[int, float]] = {}
    baseline_params: Dict[str, dict] = {}
    baseline_cache: Dict[str, dict] = {}
    baseline_times: Dict[str, np.ndarray] = {}
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

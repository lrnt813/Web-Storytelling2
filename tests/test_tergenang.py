"""Status Tergenang (Langkah 4 putaran 2)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend import thesis as T
from backend.engine import Cfg

DATA = Path(__file__).resolve().parents[1] / "data"


def test_tas_mengeluarkan_grid_tergenang():
    from tests.test_tas import _setup
    grid_xy, tes, pack = _setup()
    cfg = Cfg()
    wet = np.zeros(len(grid_xy), bool)
    wet[[0, 1, 2]] = True
    res = T.detect_tas_detour(pd.DataFrame(index=range(len(grid_xy))), grid_xy, tes, pack, 400.0, cfg,
                              tergenang=wet)
    st, s = res["status"], res["summary"]
    assert np.all(st[wet] == 3) and not np.any(st[~wet] == 3)
    assert s["jumlah_tergenang"] == 3
    assert s["jumlah_tas"] + s["jumlah_non_tas"] + s["jumlah_terputus"] + s["jumlah_tergenang"] == len(grid_xy)
    ok = (st == 0) | (st == 1)
    assert np.isclose(s["sensitivitas_persentil"]["p25_t_ideal"], np.percentile(res["t_ideal"][ok], 25))
    assert np.all(res["status_persentil"][wet] == 3)
    assert np.all(np.isnan(res["detour_index"][wet]))


@pytest.mark.skipif(not (DATA / "Kulonprogo_Ready4.gpkg").exists(), reason="data tidak tersedia")
def test_himpunan_tergenang_tidak_berkurang_saat_level_naik():
    from backend.engine import load_data, load_road_network, simulate_hazard
    cfg = Cfg(base_dir=str(DATA))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    prev = np.zeros(len(gdf), bool)
    for lv in T.LEVELS:
        _, _, _, mask = simulate_hazard(gdf, roads, tes, T.SKENARIO, lv["intensity"], cfg)
        assert np.all(mask[prev]), f"grid tergenang berkurang pada level {lv['key']}"
        prev = mask

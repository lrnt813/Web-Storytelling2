"""Smoke test endpoint utama dashboard pada keempat level (FastAPI TestClient).

Memuat seluruh data dan menjalankan simulasi, jadi lambat (beberapa menit). Jalankan dengan:
    SMOKE_API=1 python -m pytest tests/test_api_smoke.py -q
"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("SMOKE_API") != "1",
                                reason="smoke test API lambat; set SMOKE_API=1")

LEVELS = ["baseline", "rendah", "sedang", "tinggi"]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def sample_grid(client):
    rows = client.get("/api/baseline", params={"level": "baseline"}).json()
    recs = rows["data_klaster"]
    assert recs, "payload level tidak memuat rekaman grid"
    return recs[len(recs) // 2]


def test_system(client):
    assert client.get("/api/health").status_code == 200
    lv = client.get("/api/levels")
    assert lv.status_code == 200
    r = client.get("/api/thesis-results")
    assert r.status_code == 200
    res = r.json()
    ks = res["k_selection"]
    assert "ketegasan_partisi" in ks["candidates"][0] and "cdvm" not in ks["candidates"][0]
    assert ks["k_terpilih"] == res["k"] == lv.json()["k"]
    for p in ["/api/admin-layers", "/api/admin-boundaries", "/api/grid-admin", "/api/search-list"]:
        assert client.get(p).status_code == 200, p


@pytest.mark.parametrize("level", LEVELS)
def test_level_endpoints(client, sample_grid, level):
    r = client.get("/api/baseline", params={"level": level})
    assert r.status_code == 200
    body = r.json()
    recs = body["data_klaster"]
    assert {int(g["status_tas"]) for g in recs} <= {0, 1, 2}

    assert client.get("/api/tes-layers", params={"level": level}).status_code == 200
    assert client.post("/api/roads", json={"level": level}).status_code == 200
    route = client.post("/api/route-all-tes", json={"lat": sample_grid.get("lat", -7.87),
                                                    "lng": sample_grid.get("lng", 110.16),
                                                    "id_grid": sample_grid["id_grid"], "level": level})
    assert route.status_code == 200
    sim = client.post("/api/simulate", json={"level": level,
                                             "cut_roads": [{"lat": -7.8573, "lng": 110.1590}]})
    assert sim.status_code == 200, sim.text[:300]

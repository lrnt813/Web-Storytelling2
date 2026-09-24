"""Smoke test endpoint utama dashboard pada keempat level untuk setiap K keluaran (FastAPI TestClient).

Memuat seluruh data dan menjalankan simulasi, jadi lambat (beberapa menit). Jalankan dengan:
    SMOKE_API=1 python -m pytest tests/test_api_smoke.py -q
"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("SMOKE_API") != "1",
                                reason="smoke test API lambat; set SMOKE_API=1")

LEVELS = ["baseline", "rendah", "sedang", "tinggi"]
KS = [2, 3, 4]


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
    d = lv.json()
    assert sorted(d["k_keluaran"]) == KS and d["k"] == d["k_utama"]
    r = client.get("/api/thesis-results")
    assert r.status_code == 200
    res = r.json()
    assert set(res["model"]) == {"2", "3", "4"}
    assert "ari_subsampel_mean" in res["k_selection"]["candidates"][0]
    for p in ["/api/admin-layers", "/api/admin-boundaries", "/api/grid-admin", "/api/search-list"]:
        assert client.get(p).status_code == 200, p
    assert client.get("/api/baseline", params={"level": "baseline", "k": 7}).status_code == 422


@pytest.mark.parametrize("k", KS)
@pytest.mark.parametrize("level", LEVELS)
def test_level_endpoints(client, sample_grid, level, k):
    r = client.get("/api/baseline", params={"level": level, "k": k})
    assert r.status_code == 200
    body = r.json()
    assert body["k_optimal"] == k
    recs = body["data_klaster"]
    assert {int(g["status_tas"]) for g in recs} <= {0, 1, 2, 3}
    assert {g["cluster_sdwfcm"] for g in recs} <= set(range(-1, k))
    assert all((g["cluster_sdwfcm"] == -1) == (g["tergenang"] == 1) for g in recs)
    assert all(g["status_tas"] == 3 for g in recs if g["tergenang"] == 1)

    assert client.get("/api/tes-layers", params={"level": level}).status_code == 200
    assert client.post("/api/roads", json={"level": level}).status_code == 200
    route = client.post("/api/route-all-tes", json={"lat": sample_grid.get("lat", -7.87),
                                                    "lng": sample_grid.get("lng", 110.16),
                                                    "id_grid": sample_grid["id_grid"], "level": level})
    assert route.status_code == 200
    sim = client.post("/api/simulate", json={"level": level, "k": k,
                                             "cut_roads": [{"lat": -7.8573, "lng": 110.1590}]})
    assert sim.status_code == 200, sim.text[:300]
    assert sim.json()["k_optimal"] == k

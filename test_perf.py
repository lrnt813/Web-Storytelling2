import asyncio
import time
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app, startup_event, post_route, post_simulate
from backend.state import state
from backend.schemas import RouteRequest, SimulateRequest, RoadCutItem

async def test_performance():
    print("="*50)
    print("Memulai proses startup (memuat data)...")
    await startup_event()
    print(f"Status kesiapan: {state.is_ready}")
    
    if not state.is_ready:
        print("Startup gagal:", state.startup_error)
        return
        
    print("\n[UJI 1] Menguji Navigasi Rute (Grid Click)...")
    payload = RouteRequest(
        lat=-7.82,
        lng=110.15,
        skenario="banjir",
        intensity=0.5
    )
    
    # Pemanasan (Warm up)
    await post_route(payload)
    
    # Pengukuran waktu sesungguhnya
    t0 = time.time()
    res = await post_route(payload)
    t1 = time.time()
    
    print(f"Selesai dalam: {t1 - t0:.4f} detik")
    
    print("\n[UJI 2] Menguji Simulasi Blokade & Cluster...")
    simulate_payload = SimulateRequest(
        skenario="banjir",
        intensity=0.5,
        cut_roads=[RoadCutItem(lat=-7.82, lng=110.15)]
    )
    
    # Pengukuran waktu
    t0 = time.time()
    res_sim = await post_simulate(simulate_payload)
    t1 = time.time()
    
    print(f"Selesai dalam: {t1 - t0:.4f} detik")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_performance())
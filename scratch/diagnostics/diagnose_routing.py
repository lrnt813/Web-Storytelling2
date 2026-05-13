
import geopandas as gpd
import networkx as nx
from backend.engine import Cfg, load_data, load_road_network, build_road_graph, filter_tes, simulate_hazard
import os

def diagnose():
    print("--- DIAGNOSTIC START ---")
    cfg = Cfg(base_dir="data")
    
    print("1. Loading Grid...")
    gdf_base = load_data(cfg)
    print(f"   Grid: {len(gdf_base)} rows")
    
    print("2. Loading Road Network & TES...")
    roads_raw, tes_raw = load_road_network(cfg)
    print(f"   Roads: {len(roads_raw)} segments")
    print(f"   TES: {sum(len(v) for v in tes_raw.values())} points")
    
    print("3. Building Graph (Banjir, 0.0)...")
    G, nodes_list, kdtree = build_road_graph(roads_raw, "banjir", 0.0, cfg)
    print(f"   Graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
    
    print("4. Testing Filter TES...")
    # Simulate hazard at 0.0 intensity
    _, _, tes_sim, _ = simulate_hazard(gdf_base.copy(), roads_raw.copy(), tes_raw, "banjir", 0.0, cfg)
    tes_v_all, tes_stats = filter_tes(tes_sim, "banjir", cfg)
    print(f"   TES Valid (Banjir 0.0): {len(tes_v_all)} rows")
    for kat in cfg.kategori_fac:
        count = len(tes_v_all[tes_v_all["kategori"] == kat])
        print(f"      - {kat}: {count}")

    print("5. Testing Snapping for a random grid centroid...")
    sample_point = gdf_base.geometry.centroid.iloc[len(gdf_base)//2]
    from backend.main import _snap
    snapped = _snap(G, kdtree, nodes_list, [sample_point.x, sample_point.y], max_snap=1000)
    print(f"   Sample Snapped: {snapped}")

    if snapped:
        print("6. Testing Dijkstra to all nodes...")
        lengths, paths = nx.single_source_dijkstra(G, snapped, weight="weight")
        print(f"   Reachable nodes from sample: {len(lengths)}")
        
        reachable_tes = 0
        for _, row in tes_v_all.iterrows():
            nd = _snap(G, kdtree, nodes_list, [row.geometry.x, row.geometry.y], max_snap=1000)
            if nd in lengths:
                reachable_tes += 1
        print(f"   Reachable TES from sample: {reachable_tes}/{len(tes_v_all)}")

    print("--- DIAGNOSTIC END ---")

if __name__ == "__main__":
    diagnose()

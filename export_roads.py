import geopandas as gpd
import json
import os
from pathlib import Path

# Setup configuration similar to main.py
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
ROADS_FILE = DATA_DIR / "Kulonprogo_Jalan.gpkg"
OUTPUT_FILE = BASE_DIR / "frontend" / "static_roads_kulonprogo.geojson"

def export_roads():
    print(f"Loading roads from {ROADS_FILE}...")
    # Read roads, filter geometry
    roads = gpd.read_file(ROADS_FILE)
    if roads.crs is None:
        roads = roads.set_crs("EPSG:4326")
    
    # Reproject to WGS84 for Leaflet
    roads_wgs = roads.to_crs("EPSG:4326")
    
    # Filter only LineStrings
    roads_wgs = roads_wgs[roads_wgs.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    roads_wgs = roads_wgs[roads_wgs.geometry.notna() & ~roads_wgs.geometry.is_empty].reset_index(drop=True)
    
    # Simplify geometry to reduce file size (but keep it looking good)
    roads_wgs["geometry"] = roads_wgs.geometry.simplify(0.0001, preserve_topology=True)
    
    # Add id_jalan (row index) for JOINing with API
    roads_wgs["id_jalan"] = range(len(roads_wgs))
    
    # Only keep necessary columns
    cols = ["id_jalan", "geometry"]
    if "name" in roads_wgs.columns: cols.append("name")
    
    print(f"Exporting {len(roads_wgs)} segments to {OUTPUT_FILE}...")
    roads_wgs[cols].to_json(OUTPUT_FILE)
    print("Done!")

if __name__ == "__main__":
    export_roads()

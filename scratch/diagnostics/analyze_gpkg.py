import geopandas as gpd
import json

def analyze_and_export():
    try:
        kec = gpd.read_file('data/KulonProgo_Kec.gpkg')
        desa = gpd.read_file('data/KulonProgo_Desa.gpkg')
        
        print("Kecamatan Columns:", kec.columns.tolist())
        print("Desa Columns:", desa.columns.tolist())
        
        # We need a consistent way to match these with the KULON_PROGO_LIST
        # Usually the column is 'KECAMATAN' and 'DESA' or 'NAMOBJ'
        
        # Let's see some sample data to find the name column
        print("\nKecamatan Sample:\n", kec.head(3))
        print("\nDesa Sample:\n", desa.head(3))
        
        # Export to GeoJSON for frontend use
        # We might want to simplify the geometry to reduce file size
        kec = kec.to_crs(epsg=4326)
        desa = desa.to_crs(epsg=4326)
        
        kec.to_file('static/kecamatan.json', driver='GeoJSON')
        desa.to_file('static/desa.json', driver='GeoJSON')
        print("\nExported to static/kecamatan.json and static/desa.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_and_export()

import os
import json
import osmnx as ox
import geopandas as gpd
from shapely.geometry import box

# Paths
metadata_path = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\turkey2metadatas"
output_folder = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\turkey2geopackages"

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Process each metadata JSON file
for metadata_file in os.listdir(metadata_path):
    if metadata_file.endswith(".json"):  # Check if it's a JSON file
        input_metadata_path = os.path.join(metadata_path, metadata_file)
        output_osm_path = os.path.join(output_folder, f"{os.path.splitext(metadata_file)[0]}_roads.gpkg")
        
        try:
            # Step 1: Load Metadata
            with open(input_metadata_path, "r") as json_file:
                metadata = json.load(json_file)
            
            # Step 2: Extract Bounding Box and CRS
            bounding_box = (
                metadata["bounding_box"]["left"],   # west (UTM x)
                metadata["bounding_box"]["bottom"], # south (UTM y)
                metadata["bounding_box"]["right"],  # east (UTM x)
                metadata["bounding_box"]["top"]     # north (UTM y)
            )
            crs = metadata["crs"]

            print(f"Processing {metadata_file}")
            print(f"Original Bounding Box (UTM): {bounding_box}")
            print(f"Original CRS: {crs}")
            
            # Step 3: Convert UTM Bounding Box to WGS84
            # Create a GeoDataFrame for the bounding box in UTM
            bbox_gdf = gpd.GeoDataFrame(
                {"geometry": [box(*bounding_box)]},
                crs=crs  # UTM CRS from metadata
            )
            
            # Reproject to WGS84
            bbox_gdf = bbox_gdf.to_crs("EPSG:4326")
            
            # Extract the reprojected bounding box in WGS84
            bbox_wgs84 = bbox_gdf.geometry[0].bounds  # (west, south, east, north)
            west, south, east, north = bbox_wgs84
            
            print(f"Reprojected Bounding Box (WGS84): {bbox_wgs84}")
            
            # Step 4: Fetch Road Network Using OSMnx
            road_network = ox.graph_from_bbox(
                north=north, south=south, east=east, west=west, network_type="drive"
            )
            print("Road network fetched successfully.")
            
            # Step 5: Save the Road Network
            ox.save_graph_geopackage(road_network, filepath=output_osm_path)
            print(f"Road network data saved to {output_osm_path}")
        except Exception as e:
            print(f"Error processing {metadata_file}: {e}")

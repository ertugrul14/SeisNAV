import os
import json
import numpy as np
from shapely.geometry import Polygon
import geopandas as gpd
from skimage import measure
from PIL import Image

# Paths
mask_folder_path = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\turkey2roboflow_masks2"
metadata_folder_path = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\turkey2metadatas"
output_folder_path = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\turkey2geojsons2"

# Ensure output folder exists
os.makedirs(output_folder_path, exist_ok=True)

# Debug: List metadata files
print("Metadata files in the folder:")
metadata_files = os.listdir(metadata_folder_path)
print(metadata_files)

# Process each mask file in the folder
for mask_file in os.listdir(mask_folder_path):
    if mask_file.endswith("mask.png"):
        # Extract tile number without extra prefix
        tile_number = mask_file.replace("tiles", "").replace("mask.png", "")
        
        # Debug: Print extracted tile number
        print(f"\nProcessing mask file: {mask_file}, Tile number: {tile_number}")
        
        # Construct metadata filename
        metadata_filename = f"tiles{tile_number}_metadata.json"  # Ensure only one 'tiles' prefix
        geotiff_metadata_path = os.path.join(metadata_folder_path, metadata_filename)
        
        # Debug: Print constructed metadata filename
        print(f"Looking for metadata file: {metadata_filename}")
        
        # Check if metadata file exists
        if not os.path.exists(geotiff_metadata_path):
            print(f"Metadata file {metadata_filename} not found for mask {mask_file}. Skipping...")
            continue
        
        # Step 1: Load Metadata
        with open(geotiff_metadata_path, "r") as json_file:
            metadata = json.load(json_file)

        # Load mask path
        mask_path = os.path.join(mask_folder_path, mask_file)

        # Step 2: Load the Mask
        mask = np.array(Image.open(mask_path))

        # Step 3: Extract Gray Regions (Collapsed Buildings)
        gray_mask = (mask[:, :, 0] == 128) & (mask[:, :, 1] == 128) & (mask[:, :, 2] == 128)

        # Step 4: Convert Gray Regions to Polygons
        contours = measure.find_contours(gray_mask, level=0.5)
        polygons = []
        for contour in contours:
            poly = Polygon(contour[:, ::-1])  # Convert to (x, y) format
            if poly.is_valid:
                polygons.append(poly)

        if not polygons:
            print(f"No valid polygons extracted from {mask_file}. Skipping...")
            continue

        # Step 5: Transform Polygons to Geospatial Coordinates
        bounding_box = metadata["bounding_box"]
        left, bottom, right, top = bounding_box["left"], bounding_box["bottom"], bounding_box["right"], bounding_box["top"]
        image_height, image_width = metadata["dimensions"]["height"], metadata["dimensions"]["width"]

        def image_to_geospatial(x, y):
            lon = left + (x / image_width) * (right - left)
            lat = top - (y / image_height) * (top - bottom)
            return lon, lat

        geospatial_polygons = []
        for poly in polygons:
            geo_coords = [image_to_geospatial(x, y) for x, y in poly.exterior.coords]
            geospatial_polygons.append(Polygon(geo_coords))

        # Step 6: Offset the Polygons
        resolution_x = metadata["resolution"]["x"]
        resolution_y = metadata["resolution"]["y"]
        average_offset_distance = (20 * resolution_x + 20 * resolution_y) / 2
        offset_geospatial_polygons = [poly.buffer(average_offset_distance) for poly in geospatial_polygons]

        # Step 7: Create a GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=offset_geospatial_polygons, crs=metadata["crs"])

        # Output GeoJSON file
        output_geojson_filename = os.path.splitext(mask_file)[0] + ".geojson"
        output_polygons_path = os.path.join(output_folder_path, output_geojson_filename)

        # Step 8: Save as GeoJSON
        gdf.to_crs("EPSG:4326").to_file(output_polygons_path, driver="GeoJSON")
        print(f"Processed and saved {mask_file} to {output_polygons_path}.")
import os
import json
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point, LineString
import geopandas as gpd
from skimage import measure
from PIL import Image
import rasterio
import osmnx as ox
from flask import Flask, render_template, jsonify, send_from_directory, request
import networkx as nx

# Flask Application
app = Flask(__name__)

# Step 1: Extract Metadata from GeoTIFF
def extract_metadata(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for filename in os.listdir(input_folder):
        if filename.endswith(".tif"):
            tif_file_path = os.path.join(input_folder, filename)
            output_json_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_metadata.json")
            try:
                with rasterio.open(tif_file_path) as src:
                    metadata = {
                        "bounding_box": {
                            "left": src.bounds.left,
                            "bottom": src.bounds.bottom,
                            "right": src.bounds.right,
                            "top": src.bounds.top,
                        },
                        "crs": str(src.crs),
                        "resolution": {"x": src.res[0], "y": src.res[1]},
                        "dimensions": {"width": src.width, "height": src.height},
                    }
                with open(output_json_path, "w") as json_file:
                    json.dump(metadata, json_file, indent=4)
                print(f"Metadata for {filename} saved to {output_json_path}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

# Step 2: Fetch Road Network Using Metadata
def fetch_road_network(metadata_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for metadata_file in os.listdir(metadata_path):
        if metadata_file.endswith(".json"):
            input_metadata_path = os.path.join(metadata_path, metadata_file)
            output_osm_path = os.path.join(output_folder, f"{os.path.splitext(metadata_file)[0]}_roads.gpkg")
            try:
                with open(input_metadata_path, "r") as json_file:
                    metadata = json.load(json_file)
                bounding_box = (
                    metadata["bounding_box"]["left"],
                    metadata["bounding_box"]["bottom"],
                    metadata["bounding_box"]["right"],
                    metadata["bounding_box"]["top"]
                )
                crs = metadata["crs"]
                bbox_gdf = gpd.GeoDataFrame(
                    {"geometry": [Polygon.from_bounds(*bounding_box)]}, crs=crs
                )
                bbox_gdf = bbox_gdf.to_crs("EPSG:4326")
                bbox_wgs84 = bbox_gdf.geometry[0].bounds
                west, south, east, north = bbox_wgs84
                road_network = ox.graph_from_bbox(
                    north=north, south=south, east=east, west=west, network_type="drive"
                )
                ox.save_graph_geopackage(road_network, filepath=output_osm_path)
                print(f"Road network data saved to {output_osm_path}")
            except Exception as e:
                print(f"Error processing {metadata_file}: {e}")

# Step 3: Process Mask Files and Generate GeoJSONs
def process_masks(mask_folder, metadata_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for mask_file in os.listdir(mask_folder):
        if mask_file.endswith("mask.png"):
            tile_number = mask_file.replace("tiles", "").replace("mask.png", "")
            metadata_filename = f"tiles{tile_number}_metadata.json"
            geotiff_metadata_path = os.path.join(metadata_folder, metadata_filename)
            if not os.path.exists(geotiff_metadata_path):
                print(f"Metadata file {metadata_filename} not found for mask {mask_file}. Skipping...")
                continue
            with open(geotiff_metadata_path, "r") as json_file:
                metadata = json.load(json_file)
            mask_path = os.path.join(mask_folder, mask_file)
            mask = np.array(Image.open(mask_path))
            gray_mask = (mask[:, :, 0] == 128) & (mask[:, :, 1] == 128) & (mask[:, :, 2] == 128)
            contours = measure.find_contours(gray_mask, level=0.5)
            polygons = [Polygon(contour[:, ::-1]) for contour in contours if Polygon(contour[:, ::-1]).is_valid]
            if not polygons:
                print(f"No valid polygons extracted from {mask_file}. Skipping...")
                continue
            bounding_box = metadata["bounding_box"]
            left, bottom, right, top = bounding_box["left"], bounding_box["bottom"], bounding_box["right"], bounding_box["top"]
            image_height, image_width = metadata["dimensions"]["height"], metadata["dimensions"]["width"]
            def image_to_geospatial(x, y):
                lon = left + (x / image_width) * (right - left)
                lat = top - (y / image_height) * (top - bottom)
                return lon, lat
            geospatial_polygons = [Polygon([image_to_geospatial(x, y) for x, y in poly.exterior.coords]) for poly in polygons]
            resolution_x = metadata["resolution"]["x"]
            resolution_y = metadata["resolution"]["y"]
            average_offset_distance = (20 * resolution_x + 20 * resolution_y) / 2
            offset_geospatial_polygons = [poly.buffer(average_offset_distance) for poly in geospatial_polygons]
            gdf = gpd.GeoDataFrame(geometry=offset_geospatial_polygons, crs=metadata["crs"])
            output_geojson_filename = os.path.splitext(mask_file)[0] + ".geojson"
            output_polygons_path = os.path.join(output_folder, output_geojson_filename)
            gdf.to_crs("EPSG:4326").to_file(output_polygons_path, driver="GeoJSON")
            print(f"Processed and saved {mask_file} to {output_polygons_path}.")

# Step 4: Build Graph and Remove Edges
def build_graph_and_remove_edges(road_network_file, polygons_folder, output_static_folder):
    road_network = gpd.read_file(road_network_file)
    all_polygons = []
    for file_name in os.listdir(polygons_folder):
        if file_name.endswith(".geojson"):
            file_path = os.path.join(polygons_folder, file_name)
            polygons = gpd.read_file(file_path)
            all_polygons.append(polygons)

    collapsed_polygons = gpd.GeoDataFrame(pd.concat(all_polygons, ignore_index=True), crs=road_network.crs)

    # Save GeoJSON for static serving
    road_network_geojson = os.path.join(output_static_folder, "road_network.geojson")
    collapsed_polygons_geojson = os.path.join(output_static_folder, "collapsed_polygons.geojson")

    road_network.to_file(road_network_geojson, driver="GeoJSON")
    collapsed_polygons.to_file(collapsed_polygons_geojson, driver="GeoJSON")

    # Build a NetworkX graph
    G = nx.Graph()
    for _, row in road_network.iterrows():
        if row.geometry.geom_type == "LineString":
            coords = list(row.geometry.coords)
            for i in range(len(coords) - 1):
                G.add_edge(coords[i], coords[i + 1], weight=LineString([coords[i], coords[i + 1]]).length)

    # Remove edges intersecting collapsed building polygons
    for _, polygon in collapsed_polygons.iterrows():
        for edge in list(G.edges):
            line = LineString(edge)
            if polygon.geometry.intersects(line):
                G.remove_edge(*edge)

    return G

# Flask Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/road-network")
def get_road_network():
    return send_from_directory("backend/static", "road_network.geojson")

@app.route("/collapsed-polygons")
def get_collapsed_polygons():
    return send_from_directory("backend/static", "collapsed_polygons.geojson")

@app.route("/shortest-path", methods=["POST"])
def shortest_path():
    data = request.json
    start = tuple(data["start"])
    end = tuple(data["end"])

    start_node = find_nearest_node(G, start)
    end_node = find_nearest_node(G, end)

    if not nx.has_path(G, start_node, end_node):
        return jsonify({"error": "No path exists between the selected locations."}), 400

    path = nx.shortest_path(G, source=start_node, target=end_node, weight="weight")
    return jsonify({"path": path})

def find_nearest_node(graph, point):
    return min(graph.nodes, key=lambda node: Point(node).distance(Point(point)))

if __name__ == "__main__":
    # Define file paths
    road_network_file = "backend/data/road_network.gpkg"
    polygons_folder = "backend/data/polygons"
    static_folder = "backend/static"

    # Build the graph
    G = build_graph_and_remove_edges(road_network_file, polygons_folder, static_folder)

    # Run Flask app
    app.run(host='0.0.0.0', port=5555, debug=True)

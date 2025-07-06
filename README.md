🛰️ SeisNav: Seismic Navigation Planner
SeisNav is a Python-based geospatial pipeline and web application for planning navigation routes through seismic zones. It processes GeoTIFF tiles, segmentation masks, and OpenStreetMap data to extract roads, identify obstacles (e.g., collapsed buildings), and generate safe paths between user-defined points.

🚀 Features
Extracts metadata from GeoTIFF files

Downloads road networks using OSM and bounding boxes

Converts segmentation masks into geospatial polygons

Removes road segments intersecting collapsed structures

Computes shortest paths using NetworkX

Provides a simple web interface with API endpoints

🗂️ Project Structure
.
├── complete_seisnav.py       # Main Flask app and pipeline logic
├── backend/
│   ├── data/                 # Input GeoTIFF, mask, and road data
│   └── static/               # Output GeoJSONs for web access
└── templates/
    └── index.html            # Web interface (not included here)
⚙️ Installation
Clone the repository
git clone https://github.com/yourusername/seisnav.git
cd seisnav

Install dependencies
It's recommended to use a virtual environment:
pip install -r requirements.txt
Required packages include:

flask

rasterio

osmnx

geopandas

scikit-image

pillow

networkx

shapely

pandas

numpy

📦 Usage
Prepare your data

Place .tif files in an input folder

Place segmentation masks in another folder (named like tilesXXXmask.png)

Run the pipeline
In complete_seisnav.py, the following steps are automatically called in order:

Extract GeoTIFF metadata

Fetch road network

Convert mask to polygons

Remove intersecting roads

Build a pathfinding graph

Start the web server
python complete_seisnav.py

🌐 API Endpoints
/ – Web interface

/road-network – Returns cleaned road network as GeoJSON

/collapsed-polygons – Returns identified obstacles as GeoJSON

/shortest-path – POST request with:
```
{
  "start": [longitude, latitude],
  "end": [longitude, latitude]
}
```

📌 Notes
Mask polygons are buffered to account for image resolution.

The pathfinding graph only includes drivable roads that do not intersect collapsed structures.

Coordinate systems are automatically handled and reprojected to EPSG:4326 for web use.


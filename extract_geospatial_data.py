import rasterio
import os
import json

# Input and output folder paths
input_folder = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\processed_tifs"
output_folder = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\turkey2metadatas"

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Process each GeoTIFF file in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith(".tif"):  # Check if the file is a GeoTIFF
        tif_file_path = os.path.join(input_folder, filename)
        output_json_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_metadata.json")
        
        try:
            # Extract metadata
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
            
            # Save metadata as JSON
            with open(output_json_path, "w") as json_file:
                json.dump(metadata, json_file, indent=4)
            
            print(f"Metadata for {filename} saved to {output_json_path}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

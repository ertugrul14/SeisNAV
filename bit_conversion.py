import os
from osgeo import gdal

# Define input and output directories
input_folder = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\processed_tifs"
output_folder = r"D:\IAAC-1st TERM\Research Studio\SeisNAV_Code\output"

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Loop through all files in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith(".tif"):
        # Construct full file paths
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"8bit_{filename}")

        try:
            # Open the original GeoTIFF file
            dataset = gdal.Open(input_path)
            if dataset is None:
                print(f"Failed to open {filename}")
                continue

            # Read the first band (assuming single band or grayscale image)
            band = dataset.GetRasterBand(1)
            image_array = band.ReadAsArray()

            # Create an 8-bit image (clip values to 0-255 range for 8-bit conversion)
            image_array = image_array.clip(0, 255).astype('uint8')

            # Create a new GeoTIFF with 8-bit depth and the same georeferencing data
            driver = gdal.GetDriverByName('GTiff')
            out_ds = driver.Create(output_path, dataset.RasterXSize, dataset.RasterYSize, 1, gdal.GDT_Byte)

            # Set the georeferencing data and projection (preserve the original data)
            out_ds.SetProjection(dataset.GetProjection())
            out_ds.SetGeoTransform(dataset.GetGeoTransform())

            # Write the 8-bit image data to the new file
            out_ds.GetRasterBand(1).WriteArray(image_array)

            # Clean up
            out_ds = None
            dataset = None

            print(f"8-bit GeoTIFF saved with georeferencing to {output_path}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

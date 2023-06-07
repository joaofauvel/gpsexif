import csv
import logging
import os
from pathlib import Path

from rich.progress import track
import typer
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

app = typer.Typer()
logger = logging.getLogger(__name__)

# function to extract GPS data from EXIF tags
def get_exif_data(image):
    exif_data = {}
    try:
        img = Image.open(image)
        info = img._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == 'GPSInfo':
                    gps_data = {}
                    for gps_tag in value:
                        gps_decoded = GPSTAGS.get(gps_tag, gps_tag)
                        gps_data[gps_decoded] = value[gps_tag]
                    exif_data[decoded] = gps_data
                else:
                    exif_data[decoded] = value
    except Exception as e:
        logger.error(f"Error getting exif data for image {image}: {e}")
    return exif_data

# function to convert GPS coordinates from degrees, minutes, seconds to decimal degrees
def convert_to_degrees(value):
    logger.debug(f"value type: {type(value)}")
    logger.debug(f"value: {value}")
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)

# function to write point geometry file with image path in a field called 'Path'
def write_point_geometry_file(images, outfile):
    with open(outfile, 'w', newline='') as csvfile:
        fieldnames = ['Path', 'Latitude', 'Longitude']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        total = 0
        for image in track(images, description="Processing..."):
            exif_data = get_exif_data(image)
            if 'GPSInfo' in exif_data:
                gps_info = exif_data['GPSInfo']
                logger.debug(f"gps_info['GPSLatitude']: {gps_info['GPSLatitude']}")
                gps_latitude = convert_to_degrees(gps_info['GPSLatitude'])
                gps_latitude_ref = gps_info['GPSLatitudeRef']
                if gps_latitude_ref == 'S':
                    gps_latitude = -gps_latitude
                logger.debug(f"gps_info['GPSLongitude']: {gps_info['GPSLongitude']}")
                gps_longitude = convert_to_degrees(gps_info['GPSLongitude'])
                gps_longitude_ref = gps_info['GPSLongitudeRef']
                if gps_longitude_ref == 'W':
                    gps_longitude = -gps_longitude
                image_path = Path(image)
                path = str(image_path.resolve())
                writer.writerow(
                    {'Path': path, 'Latitude': gps_latitude, 'Longitude': gps_longitude})
                total += 1
        print(f"Processed {total} things.")

# main function to find all JPEG images in a directory and its subdirectories and write the point geometry file
@app.command()
def run(
    directory: str = typer.Argument(..., help="Directory to search for images"),
    outfile: str = typer.Argument(..., help="Output file path"),
    verbose: int = typer.Option(0, "-v", count=True, help="Increase logging level"),
):
    log_levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    # set up logging
    logging.basicConfig(
        format='%(levelname)s:%(message)s',
        level=log_levels[min(verbose, len(log_levels) - 1)]
    )
    images = []
    for root, dirs, files in os.walk(directory):
        # loop through all the files in the current directory
        for file in files:
            # check if the file is a JPEG image
            if file.lower().endswith('.jpg') or file.lower().endswith('.jpeg'):
                # add the file to the list of images
                images.append(os.path.join(root, file))

    # write the point geometry file
    write_point_geometry_file(images, outfile)

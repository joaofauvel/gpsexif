from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
import csv
import typer

app = typer.Typer()

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
        print(f"Error getting exif data for image {image}: {e}")
    return exif_data

# function to convert GPS coordinates from degrees, minutes, seconds to decimal degrees
def convert_to_degrees(value):
    d = float(value[0][0]) / float(value[0][1])
    m = float(value[1][0]) / float(value[1][1])
    s = float(value[2][0]) / float(value[2][1])
    return d + (m / 60.0) + (s / 3600.0)

# function to write point geometry file with image path in a field called 'Path'
def write_point_geometry_file(images, outfile):
    with open(outfile, 'w', newline='') as csvfile:
        fieldnames = ['Path', 'Latitude', 'Longitude']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for image in images:
            exif_data = get_exif_data(image)
            if 'GPSInfo' in exif_data:
                gps_info = exif_data['GPSInfo']
                gps_latitude = convert_to_degrees(gps_info['GPSLatitude'])
                gps_latitude_ref = gps_info['GPSLatitudeRef']
                if gps_latitude_ref == 'S':
                    gps_latitude = -gps_latitude
                gps_longitude = convert_to_degrees(gps_info['GPSLongitude'])
                gps_longitude_ref = gps_info['GPSLongitudeRef']
                if gps_longitude_ref == 'W':
                    gps_longitude = -gps_longitude
                path = os.path.join(os.path.relpath(os.path.dirname(image)), os.path.basename(image))
                writer.writerow({'Path': path, 'Latitude': gps_latitude, 'Longitude': gps_longitude})

# main function to find all JPEG images in a directory and its subdirectories and write the point geometry file
@app.command()
def main(
    directory: str = typer.Argument(..., help="Directory to search for images"),
    outfile: str = typer.Argument(..., help="Output file path"),
):
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



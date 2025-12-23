import sys, os
import traceback

import json
import time
import datetime
from line_profiler import profile

import OpenEXR

import faulthandler
faulthandler.enable()

import recompress_oiio

COMPRESSION_METHODS = {
    "NO_COMPRESSION",
    "RLE_COMPRESSION",
    "ZIPS_COMPRESSION",
    "ZIP_COMPRESSION",
    "PIZ_COMPRESSION",
    "PXR24_COMPRESSION",
    "B44_COMPRESSION",
    "B44A_COMPRESSION",
    "DWAA_COMPRESSION",
    "DWAB_COMPRESSION",
    "HTJ2K256_COMPRESSION",
    "HTJ2K32_COMPRESSION"
}

image_dir = "./images"
temp_dir = "./temp"
results = []
result_dir = "./results"

def remove_files(dir):

    for root, dirs, files in os.walk(dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            print('file', file_path)
            os.remove(file_path)

@profile
def go_over_files(compression_method):
    start = time.perf_counter()
    compression_name = compression_method.split("_")[0]
    for root, dirs, files in os.walk(image_dir):
        for filename in files:
            old_file_path = os.path.join(root, filename)

            if old_file_path.endswith(".exr"):
                filename_parts = filename.split(".")
                exr = OpenEXR.InputFile(old_file_path)
                new_file_path = os.path.join(temp_dir, filename_parts[0].split('_')[0] + '_' + compression_name + '.' + filename_parts[1])
                s = time.process_time()  # start time


                recompress_oiio.recompress(old_file_path, new_file_path, compression=compression_method)

                e = time.process_time()  # end time
                duration = e - s
                results.append({"compression": compression_method,"file": str(old_file_path), "duration": duration})

def go_over_compression():
    for compression in COMPRESSION_METHODS:
        go_over_files(compression)
    # go_over_files('PIZ_COMPRESSION')

    remove_files(temp_dir)

    result_file = result_dir + '/' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.json'
    # json.dump(results, result_file)


    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


go_over_compression()
print(results)



# with OpenEXR.File("image.exr") as infile:
#
#     header = infile.header()
#     print(f"type={header['type']}")
#     print(f"compression={header['compression']}")
#
#     RGB = infile.channels()["RGB"].pixels
#     height, width = RGB.shape[0:2]
#     for y in range(height):
#         for x in range(width):
#             pixel = (RGB[y, x, 0], RGB[y, x, 1], RGB[y, x, 2])
#             print(f"pixel[{y}][{x}]={pixel}")
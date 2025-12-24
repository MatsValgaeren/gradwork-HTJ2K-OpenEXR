import os

import json
import time
import datetime
from line_profiler import profile
import tempfile
import shutil

import OpenImageIO as oiio
import numpy as np

import faulthandler
faulthandler.enable()

import recompress_oiio

os.environ['OPENEXR_NUM_THREADS'] = '0'

compression_map = {
    'NO_COMPRESSION': 'none',
    'RLE_COMPRESSION': 'rle',
    'ZIP_COMPRESSION': 'zip',
    'PIZ_COMPRESSION': 'piz',
    'ZIPS_COMPRESSION': 'zips',
    'PXR24_COMPRESSION': 'pxr24',
    'B44_COMPRESSION': 'b44',
    'B44A_COMPRESSION': 'b44a',
    'DWAA_COMPRESSION': 'dwaa',
    'DWAB_COMPRESSION': 'dwab',
    'HTJ2K32_COMPRESSION': 'htj2k',
    'HTJ2K256_COMPRESSION': 'htj2k'
}

image_dir = "./images"
temp_dir = "./temp"
results = []
result_dir = "./results"
passes = 10

def remove_files(dir):
    for root, dirs, files in os.walk(dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            print('file', file_path)
            # os.remove(file_path)

@profile
def go_over_files(compression_method):
    start = time.perf_counter()
    compression_name = compression_method.split("_")[0]
    for root, dirs, files in os.walk(image_dir):
        for filename in files:
            old_file_path = os.path.join(root, filename)

            if old_file_path.endswith(".exr"):
                filename_parts = filename.split(".")

                new_file_path = os.path.join(temp_dir, filename[:-6] + compression_name + '.exr')
                print('new', new_file_path)
                oiio_comp = compression_map.get(compression_method)

                compression_res = recompress_oiio.recompress(old_file_path, new_file_path, compression=oiio_comp, passes=passes)

                res = {'copy': [], 'read': []}

                for _ in range(passes):
                    dst_copy = tempfile.NamedTemporaryFile(suffix=".exr", delete=False)
                    dst_copy.close()
                    start = time.perf_counter()
                    shutil.copyfile(new_file_path, dst_copy.name)
                    # Optionally fsync to force write to physical disk
                    with open(dst_copy.name, "rb+") as f:
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except OSError:
                            pass
                    res['copy'].append(time.perf_counter() - start)


                    s_read = time.perf_counter()
                    oiio.ImageBuf(new_file_path)
                    res['read'].append((time.perf_counter()  - s_read) * 1000)  # ms

                dur_read = np.mean(res['read'])
                dur_copy = np.mean(res['copy'])

                results.append({"compression": compression_method,"file": filename[:-7], "read_duration": dur_read, "write_duration": compression_res['compress_write_ms'], "file_size": compression_res['size_kb'], "copy": dur_copy})

def go_over_compression():
    for compression in compression_map:
        go_over_files(compression)
    # go_over_files('PIZ_COMPRESSION')

    remove_files(temp_dir)

    result_file = result_dir + '/data_' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.json'
    # json.dump(results, result_file)


    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


go_over_compression()
# print(results)

import OpenImageIO as oiio
import numpy as np

import os
import OpenEXR

for root, dirs, files in os.walk(temp_dir):
    for filename in files:
        print('start')
        file_path = os.path.join(root, filename)
        print('filepath ', file_path)

        infile = OpenEXR.InputFile(file_path)
        header = infile.header()
        comp = header['compression']
        print(f"Compression: {comp}")
        infile.close()

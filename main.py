import os
import json
import time
import datetime
from line_profiler import profile
import tempfile
import shutil

import OpenImageIO as oiio
import numpy as np
import platform
import psutil

import faulthandler
faulthandler.enable()

import recompress_oiio
import roi_test


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

os.environ['OMP_NUM_THREADS'] = '1'

image_dir = "./images"
temp_dir = r"E:\temp"
# temp_dir = "./temp"
temp = r'C:\Users\matsv\AppData\Local\Temp'
results = []
passes = 2
result_dir = "./results"
pc_usage = {}


def clean_system_cache():
    # time.sleep(0.1)
    pass


def remove_files(dir):
    for root, dirs, files in os.walk(dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            print('file', file_path)
            os.remove(file_path)

@profile
def go_over_files(num_cores, compression_method, input_dir):
    compression_name = compression_method.split("_")[0]
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            old_file_path = os.path.join(root, filename)
            print(old_file_path)

            if old_file_path.endswith(".exr"):
                filename_parts = filename.split(".")

                new_file_path = os.path.join(temp_dir, filename[:-6] + compression_name + '.exr')
                oiio_comp = compression_map.get(compression_method)

                compression_res = recompress_oiio.recompress(old_file_path, new_file_path, comp=oiio_comp, passes=passes)


                res = {'copy': [], 'read': []}

                for _ in range(passes):
                    dst_copy = tempfile.NamedTemporaryFile(suffix=".exr", delete=False)
                    dst_copy.close()

                    start = time.perf_counter()

                    shutil.copyfile(new_file_path, dst_copy.name)
                    with open(dst_copy.name, "rb+") as f:
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except OSError:
                            pass
                    res['copy'].append(time.perf_counter() - start)
                    # os.remove(new_file_path)

                for _ in range(passes):
                    start = time.perf_counter()
                    buf = oiio.ImageBuf(new_file_path)  # Metadata + header decode
                    full_pixels = buf.get_pixels()

                    res['read'].append((time.perf_counter() - start) * 1000)

                cpu_usage = psutil.cpu_percent()
                ram_usage = psutil.virtual_memory()

                roi_res = test_roi(new_file_path, compression_method)

                dur_read = np.mean(res['read'])
                dur_copy = np.mean(res['copy'])

                results.append({"processor": platform.processor(),
                                "cores": num_cores,
                                "method": compression_method,
                                "file": filename[:-7],
                                "read_ms": dur_read,
                                "write_ms": compression_res['write_ms'],
                                "size_kb": compression_res['size_kb'],
                                "cpu_ms": cpu_usage,
                                "ram_usage": ram_usage[2],
                                "copy": dur_copy,
                                "ROI": roi_res}
                               )



ROIS = [
    (0.0, 0.0, 1.0, 1.0),  # 100% full frame (baseline)
    (0.1, 0.1, 0.4, 0.4),  # 25% center (Nuke viewport)
    (0.4, 0.4, 0.6, 0.6),  # 4% center (extreme zoom)
    (0.0, 0.0, 0.5, 0.5)  # 25% top-left quadrant
]



def test_roi(file, method):
    clean_system_cache()
    try:
        return roi_test.benchmark_roi(file, ROIS)
    except Exception as e:
        print(f"✗ CRASH {file}: {e}")
        return None

def go_over_compression(num_threads):
    for compression in compression_map:
        print(compression)
        go_over_files(num_threads, compression, image_dir)
        remove_files(temp_dir)
        # remove_files(temp)
        clean_system_cache()

    result_file = result_dir + '/file-data_' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.json'

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


oiio.attribute("threads", 1)
go_over_compression(num_threads = 1)

# oiio.attribute("threads", os.cpu_count())
# go_over_compression(num_threads = os.cpu_count())


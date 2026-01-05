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



image_dir = "./images"
temp_dir = r"E:\temp"
temp_dir = "./temp"
os.makedirs(temp_dir, exist_ok=True)
temp = r'C:\Users\matsv\AppData\Local\Temp'
results = []
passes = 1
result_dir = "./results"
pc_usage = {}


def clean_system_cache():
    # time.sleep(0.1)
    pass


def psnr_simple(orig_array, comp_array):
    """PSNR for NumPy arrays from get_pixels()"""
    mse = np.mean((orig_array - comp_array) ** 2)
    if mse == 0:
        return 100.0
    max_pixel = 1.0  # EXR normalized [0,1]
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return round(psnr, 2)


def compute_psnr_roi_numpy(original_path, compressed_path, roi_fractions):
    orig_buf = oiio.ImageBuf(original_path)
    comp_buf = oiio.ImageBuf(compressed_path)

    w, h = orig_buf.spec().width, orig_buf.spec().height
    psnr_results = {}

    for roi_name, (x1, y1, x2, y2) in zip(
            ['ROI_0%-100%', 'ROI_0%-50%', 'ROI_50%-100%', 'ROI_25%-75%',
             'ROI_10%-40%', 'ROI_45%-55%', 'ROI_hstrip', 'ROI_vstrip'],
            roi_fractions):
        roi = oiio.ROI(int(x1 * w), int(x2 * w), int(y1 * h), int(y2 * h))

        orig_roi = orig_buf.get_pixels(roi=roi)  # NumPy array
        comp_roi = comp_buf.get_pixels(roi=roi)  # NumPy array

        psnr_results[roi_name] = psnr_simple(orig_roi, comp_roi)

    return psnr_results


def remove_files(dir):
    for root, dirs, files in os.walk(dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            os.remove(file_path)

def go_over_files(num_cores, compression_method, input_dir):
    compression_name = compression_method.split("_")[0]
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            old_file_path = os.path.join(root, filename)
            if old_file_path.endswith(".exr"):
                filename_parts = filename.split(".")

                new_file_path = os.path.join(temp_dir, filename[:-6] + compression_name + '.exr')
                print(new_file_path)
                oiio_comp = compression_map.get(compression_method)

                compression_res = recompress_oiio.recompress(old_file_path, new_file_path, comp=oiio_comp, passes=passes)

                # if compression_res is None:
                #     print(f"✗ Skip {filename}: write failed")
                #     continue

                res = {'copy': [], 'read': []}

                for _ in range(passes):
                    dst_copy = tempfile.NamedTemporaryFile(suffix=".exr", delete=False)
                    dst_copy.close()

                    start = time.perf_counter()

                    try:
                        shutil.copyfile(new_file_path, dst_copy.name)
                        res['copy'].append(time.perf_counter() - start)
                    finally:
                        os.remove(dst_copy.name)

                for _ in range(passes):
                    start = time.perf_counter()
                    buf = oiio.ImageBuf(new_file_path)
                    full_pixels = buf.get_pixels()

                    res['read'].append((time.perf_counter() - start) * 1000)

                cpu_usage = psutil.cpu_percent()
                ram_usage = psutil.virtual_memory()

                # buf.clear()
                res['roi'] = []  # Initialize as empty list before loop
                for _ in range(passes):
                    roi_pass = test_roi(new_file_path, compression_method)
                    res['roi'].append(roi_pass)

                # After loop: average the values
                roi_list = res['roi']
                roi_avg = {}
                keys = roi_list[0].keys()
                for key in keys:
                    values = [d[key] for d in roi_list]
                    roi_avg[key] = sum(values) / len(values)

                psnr_roi = compute_psnr_roi_numpy(old_file_path, new_file_path, ROIS)

                dur_read = np.mean(res['read'])
                dur_copy = np.mean(res['copy'])

                psnr_roi_serializable = {k: float(v) for k, v in psnr_roi.items()}
                roi_avg_serializable = {k: float(v) for k, v in roi_avg.items()}

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
                                "roi_decode_ms": roi_avg_serializable,
                                "roi_psnr_db": psnr_roi_serializable
                                })



ROIS = [
    (0.0, 0.0, 1.0, 1.0),      # Full frame (100% baseline)
    (0.0, 0.0, 0.5, 0.5),      # Top-left quadrant (25%)
    (0.5, 0.5, 1.0, 1.0),      # Bottom-right quadrant (25%)
    (0.25, 0.25, 0.75, 0.75),  # Central 50% square
    (0.1, 0.1, 0.4, 0.4),      # Small center (Nuke viewport ~9%)
    (0.45, 0.45, 0.55, 0.55),  # Tiny center (1% extreme test)
    (0.0, 0.4, 1.0, 0.6),      # Horizontal center strip (20% height)
    (0.4, 0.0, 0.6, 1.0)       # Vertical center strip (20% width)
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
        # oiio.attribute("texturecache", 0)
        go_over_files(num_threads, compression, image_dir)
        # shutil.rmtree(temp_dir, ignore_errors=True)

        remove_files(temp_dir)

    result_file = result_dir + '/file-data_' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.json'

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

total_start = time.perf_counter()
# os.environ['OMP_NUM_THREADS'] = '1'
oiio.attribute("threads", 1)
go_over_compression(num_threads = 1)

oiio.attribute("threads", os.cpu_count())
go_over_compression(num_threads = os.cpu_count())

print((time.perf_counter() - total_start))

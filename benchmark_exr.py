import os
import json
import time
import datetime
import shutil

import OpenImageIO as oiio
import numpy as np
import platform

import recompress_oiio
import roi_test

# GLOBALS
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
    'HTJ2K32_COMPRESSION':  'htj2k:rate=32',
    'HTJ2K256_COMPRESSION': 'htj2k:rate=256'
}

ROIS = [
    (0.0, 0.0, 1.0, 1.0), # Full (baseline)
    (0.1, 0.1, 0.4, 0.4) , # Viewport 9% (Nuke reality)
    (0.45, 0.45, 0.55, 0.55), # Tiny 1% (compositor extreme)
    (0.25, 0.25, 0.75, 0.75) # Central 50% (tracking/matchmove)
]


PASSES = 1
image_dir = "./images"
os.makedirs(image_dir, exist_ok=True)
temp_dir = "./temp"
os.makedirs(temp_dir, exist_ok=True)
result_dir = "./results"
os.makedirs(result_dir, exist_ok=True)


def go_over_cores():
    total_start = time.perf_counter()

    oiio.attribute("threads", 1)
    go_over_compression(num_threads = 1)

    oiio.attribute("threads", os.cpu_count())
    go_over_compression(num_threads = os.cpu_count())

    elapsed = time.perf_counter() - total_start

    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)

    print(f"{int(hours)}h {int(minutes)}m {seconds:.2f}s")

def go_over_compression(num_threads):
    results = []
    for compression in compression_map:
        results.extend(go_over_files(num_threads, compression, image_dir))
        remove_files(temp_dir)
    result_file = result_dir + '/file-data_' + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.json'

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

def go_over_files(num_cores, compression_method, input_dir, calc_tile=False):
    results = []
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            res_scan = go_over_scantile(root, filename, compression_method, scan=True)

            results.append({
                "processor": platform.processor(),
                "cores": num_cores,
                "method": compression_method,
                "file": filename[:-7],
                "group": os.path.basename(root),

                # SCAN
                "scan": {
                    "read_ms": res_scan["read_ms"],
                    "write_ms": res_scan['write_ms'],
                    "size_kb": res_scan['size_kb'],
                    "roi_decode_ms": res_scan["roi_decode_ms"],
                    "roi_psnr_db": res_scan["roi_psnr_db"]
                }
            })

            if calc_tile:
                res_tile = go_over_scantile(root, filename, compression_method, scan=False)

                results.append({
                    "tiled": {
                        "read_ms": res_tile["read_ms"],
                        "write_ms": res_tile['write_ms'],
                        "size_kb": res_tile['size_kb'],
                        "roi_decode_ms": res_tile["roi_decode_ms"],
                        "roi_psnr_db": res_tile["roi_psnr_db"]
                    }
                })
    return results

def go_over_scantile(root, filename, compression_method, scan=True, calc_roi=False):
    old_file_path = os.path.join(root, filename)
    compression_name = compression_method.split("_")[0]

    ext = 'scan'
    if not scan:
        ext = 'tile'

    # metadata
    buf = oiio.ImageBuf(old_file_path)
    spec = buf.spec()

    # res
    width = spec.width
    height = spec.height

    # bit depth
    bit_depth = 0
    for ch in range(spec.nchannels):
        fmt = spec.channelformat(ch)
        bit_depth = max(bit_depth, fmt.basesize() * 8)

    # AOVs
    nchannels = spec.nchannels
    aov_names = spec.channelnames

    # color space
    color_space = spec.getattribute("ocio:ColorSpace", 0, str) or "linear"

    if old_file_path.endswith(".exr"):
        new_file_path = os.path.join(temp_dir, filename[:-6] + compression_name)
        new_file_path += '_' + ext + '.exr'
        print(new_file_path)

        oiio_comp = compression_map.get(compression_method)

        comp_res = recompress_oiio.recompress(old_file_path, new_file_path, comp=oiio_comp, scanline=scan, passes=PASSES)

        res = {'read': []}

        temps = []
        for i in range(PASSES):
            # cold cache
            tmp = new_file_path.replace(".exr", f"_p{i}.exr")
            temps.append(tmp)
            shutil.copyfile(new_file_path, tmp)

            start = time.perf_counter()
            buf = oiio.ImageBuf(tmp)
            res['read'].append((time.perf_counter() - start) * 1000)

            os.remove(tmp)

        dur_read = np.mean(res['read'])

        roi_avg_serializable = []
        psnr_roi_serializable = []

        if calc_roi is False:
            roi_pass = roi_test.benchmark_roi(new_file_path, ROIS)
            res['roi'] = [roi_pass] if roi_pass else []

            roi_list = res['roi']
            roi_avg = {}
            keys = roi_list[0].keys()
            for key in keys:
                values = [d[key] for d in roi_list]
                roi_avg[key] = sum(values) / len(values)

            psnr_roi = compute_psnr_roi_numpy(old_file_path, new_file_path, ROIS)

            psnr_roi_serializable = {k: float(v) for k, v in psnr_roi.items()}
            roi_avg_serializable = {k: float(v) for k, v in roi_avg.items()}

        return ({
            "width": width,
            "height": height,
            "bit_depth": bit_depth,
            "num_aovs": nchannels,
            "aov_names": aov_names,
            "color_space": color_space,

            "read_ms": dur_read,
            "write_ms": comp_res['write_ms'],
            "size_kb": comp_res['size_kb'],

            "roi_decode_ms": roi_avg_serializable,
            "roi_psnr_db": psnr_roi_serializable
        })

def compute_psnr_roi_numpy(original_path, compressed_path, roi_fractions):
    orig_buf = oiio.ImageBuf(original_path)
    comp_buf = oiio.ImageBuf(compressed_path)

    w, h = orig_buf.spec().width, orig_buf.spec().height
    psnr_results = {}

    for roi_name, (x1, y1, x2, y2) in zip(
            ['full', 'viewport9', 'tiny1', 'central50'],
            roi_fractions):
        roi = oiio.ROI(int(x1 * w), int(x2 * w), int(y1 * h), int(y2 * h))

        orig_roi = orig_buf.get_pixels(roi=roi)  # NumPy array
        comp_roi = comp_buf.get_pixels(roi=roi)  # NumPy array

        psnr_results[roi_name] = psnr_simple(orig_roi, comp_roi)

    return psnr_results

def psnr_simple(orig_array, comp_array):
    mse = np.mean((orig_array - comp_array) ** 2)
    if mse == 0:
        return 100.0
    max_pixel = 1.0  # EXR normalized [0,1]
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return round(psnr, 2)

def remove_files(dir):
    for root, dirs, files in os.walk(dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            os.remove(file_path)

go_over_cores()
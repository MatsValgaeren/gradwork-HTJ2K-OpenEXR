import os
os.environ['OIIO_TMPDIR'] = ':ram:'  # RAM-only (run BEFORE import oiio)
os.environ['OIIO_CACHE_PATH'] = ''   # Disable disk cache

import OpenImageIO as oiio
import time
import numpy as np
import subprocess
img = r'C:\Users\matsv\Desktop\gw\scripts\images'
in_image_dir = "./../source"

def test(image_path):
    results = {}
    buf = oiio.ImageBuf(image_path)


    spec = buf.spec()  # Copy spec
    width, height = spec.width, spec.height

    # SHOW THREADING INFO
    if spec.tile_width > 0:
        print(image_path)
        print(f"Image: {image_path}")
        print(f"  Size: {spec.width}x{spec.height}")
        print(f"  Tiled: {spec.tile_width > 0}, Tile size: {spec.tile_width}x{spec.tile_height}")
        print(f"  Channels: {spec.nchannels}")
        print(f"  Format: {spec.format}")

    return

def benchmark_roi(image_path, roi_fractions):
    results = {}

    for xfrac1, yfrac1, xfrac2, yfrac2 in roi_fractions:
        x1, x2 = int(xfrac1 * 100), int(xfrac2 * 100)
        key = f'ROI_{x1}%-{x2}%'

        try:
            start = time.perf_counter()

            buf = oiio.ImageBuf(image_path)  # cold open + decode for each ROI
            if buf.has_error:
                continue

            spec = buf.spec()
            width, height = spec.width, spec.height
            xbegin, xend = int(width * xfrac1), int(width * xfrac2)
            ybegin, yend = int(height * yfrac1), int(height * yfrac2)

            if xbegin >= xend or ybegin >= yend:
                continue

            roi = oiio.ROI(xbegin, xend, ybegin, yend)
            _ = buf.get_pixels(roi=roi)

            end = time.perf_counter()
            results[key] = round((end - start) * 1000, 2)

        except Exception:
            continue

    return results

# for root, dirs, files in os.walk(in_image_dir):
#     for filename in files:
#         if filename.endswith(".exr"):
#             file_path = os.path.join(root, filename)
#             test(file_path)
#
# for root, dirs, files in os.walk(img):
#     for filename in files:
#         if filename.endswith(".exr"):
#             file_path = os.path.join(root, filename)
#             test(file_path)
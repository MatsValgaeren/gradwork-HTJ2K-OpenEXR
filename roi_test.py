import os
os.environ['OIIO_TMPDIR'] = ':ram:'  # RAM-only (run BEFORE import oiio)
os.environ['OIIO_CACHE_PATH'] = ''   # Disable disk cache

import OpenImageIO as oiio
import time
img = r'C:\Users\matsv\Desktop\gw\scripts\images'
in_image_dir = "./../source"


def benchmark_roi(image_path, roi_fractions):
    buf = oiio.ImageBuf(image_path)
    if buf.has_error:
        return {}

    spec = buf.spec()
    width, height = spec.width, spec.height
    results = {}

    for xfrac1, yfrac1, xfrac2, yfrac2 in roi_fractions:
        x1, x2 = int(xfrac1 * 100), int(xfrac2 * 100)
        key = f'ROI_{x1}%-{x2}%'

        start = time.perf_counter()
        roi = oiio.ROI(int(width * xfrac1), int(width * xfrac2),
                       int(height * yfrac1), int(height * yfrac2))
        _ = buf.get_pixels(roi=roi)
        results[key] = round((time.perf_counter() - start) * 1000, 2)

    return results
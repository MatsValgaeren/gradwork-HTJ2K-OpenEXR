import os
os.environ['OIIO_TMPDIR'] = ':ram:'  # RAM-only (run BEFORE import oiio)
os.environ['OIIO_CACHE_PATH'] = ''   # Disable disk cache

import OpenImageIO as oiio
import time
import numpy as np
import subprocess

def _has_multiple_subimages_or_views(path):
    inp = None
    try:
        inp = oiio.ImageInput.open(path)
        if not inp:
            return False

        nsub = None
        if hasattr(inp, "nsubimages"):
            try:
                nsub = inp.nsubimages()
            except Exception:
                nsub = None

        if nsub is None:
            nsub = 0
            while True:
                try:
                    ok = False
                    try:
                        ok = inp.seek_subimage(nsub, 0)
                    except TypeError:
                        ok = inp.seek_subimage(nsub)
                except Exception:
                    ok = False
                if not ok:
                    break
                nsub += 1

        views_present = False
        try:
            try:
                inp.seek_subimage(0, 0)
            except TypeError:
                inp.seek_subimage(0)
            spec0 = inp.spec()
            for key in ("oiio:views", "views", "view", "multiView"):
                try:
                    if hasattr(spec0, "get_string_attribute"):
                        val = spec0.get_string_attribute(key)
                    else:
                        val = spec0.get_string_attribute(key) if hasattr(spec0, "get_string_attribute") else None
                    if val:
                        views_present = True
                        break
                except Exception:
                    pass
        except Exception:
            pass

        inp.close()
        inp = None

        return (nsub > 1) or views_present

    except Exception:
        try:
            if inp:
                inp.close()
        except Exception:
            pass
        return False


def benchmark_roi(image_path, roi_fractions, n_runs=1):
    results = {}
    if _has_multiple_subimages_or_views(image_path):
        print(f"Skipping multi-subimage / multi-view file: {image_path}")
        return results

    buf = oiio.ImageBuf(image_path)


    spec = buf.spec()  # Copy spec
    width, height = spec.width, spec.height

    try:
        full_pixels = buf.get_pixels()
    except Exception as e:
        print(f"Error reading full pixels from {image_path}: {e}")
        return results

    for xfrac1, yfrac1, xfrac2, yfrac2 in roi_fractions:
        try:
            # COLD: Fresh ImageBuf EVERY ROI (matches read_ms exactly)
            start = time.perf_counter()

            buf = oiio.ImageBuf(image_path)  # Fresh file open + decode
            if buf.has_error:
                continue

            spec = buf.spec()
            width, height = spec.width, spec.height
            xbegin, xend = int(width * xfrac1), int(width * xfrac2)
            ybegin, yend = int(height * yfrac1), int(height * yfrac2)

            if xbegin >= xend or ybegin >= yend:
                continue

            roi = oiio.ROI(xbegin, xend, ybegin, yend)
            pixels = buf.get_pixels(roi=roi)
            end = time.perf_counter()

            results[f'ROI_{int(xfrac1 * 100)}%-{int(xfrac2 * 100)}%'] = round((end - start) * 1000, 2)

        except Exception:
            continue

    try:
        del buf
    except Exception:
        pass

    return results
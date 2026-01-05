import os

from OpenImageIO.OpenImageIO import ImageSpec

os.environ['OIIO_TMPDIR'] = ':ram:'  # RAM-only (run BEFORE import oiio)
os.environ['OIIO_CACHE_PATH'] = ''   # Disable disk cache

import OpenImageIO as oiio
import time
import numpy as np
import psutil

def test(image_path):
    results = {}
    buf = oiio.ImageBuf(image_path)

    spec = buf.spec()  # Copy spec
    width, height = spec.width, spec.height

    # SHOW THREADING INFO
    return spec.tile_width

def recompress(in_path, out_path, comp='none', num_threads=1, passes=1):
    process = psutil.Process()
    start_cpu = process.cpu_times()
    write_times = []

    buf = oiio.ImageBuf(in_path)
    spec = buf.spec()
    n_sub = buf.subimage
    # print(n_sub)

    for _ in range(passes):
        s_write = time.perf_counter()

        output_buf = buf.copy()

        spec = output_buf.spec().copy()
        spec.attribute("compression", comp)

        spec.tile_width = buf.spec().tile_width
        spec.tile_height = buf.spec().tile_height
        spec.tile_depth = buf.spec().tile_depth

        out = oiio.ImageOutput.create(out_path)
        if not out:
            raise RuntimeError("Could not create ImageOutput")

        if not out.open(out_path, spec):
            raise RuntimeError(out.geterror())

        # Write pixels from the ImageBuf
        out.write_image(output_buf.get_pixels())
        out.close()

        e_write = time.perf_counter()

        if os.path.exists(out_path):
            write_times.append((e_write - s_write) * 1000)

        if test(in_path) != test(out_path):
            print('tiles not the same')
    end_cpu = process.cpu_times()
    cpu_ms = ((end_cpu.user + end_cpu.system) - (start_cpu.user + start_cpu.system)) / passes * 1000

    size_kb = os.path.getsize(out_path) / 1024

    return {
        'write_ms': np.mean(write_times),
        'total_cpu_ms': cpu_ms,
        'size_kb': size_kb
    }


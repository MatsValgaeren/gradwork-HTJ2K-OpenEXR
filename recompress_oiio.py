import os

os.environ['OIIO_TMPDIR'] = ':ram:'  # RAM-only (run BEFORE import oiio)
os.environ['OIIO_CACHE_PATH'] = ''   # Disable disk cache

import OpenImageIO as oiio
import time
import numpy as np
import psutil

def recompress(in_path, out_path, comp='none', scanline=True, passes=1):
    process = psutil.Process()
    start_cpu = process.cpu_times()
    write_times = []

    buf = oiio.ImageBuf(in_path)
    spec = buf.spec()
    n_sub = buf.subimage

    for _ in range(passes):
        output_buf = buf.copy()

        spec = output_buf.spec().copy()
        spec.attribute("compression", comp)

        if scanline:
            spec.tile_width = 0
            spec.tile_height = 0
            spec.tile_depth = 0
        else:
            spec.tile_width = 64
            spec.tile_height = 64
            spec.tile_depth = 1

        s_write = time.perf_counter()

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

    end_cpu = process.cpu_times()
    cpu_ms = ((end_cpu.user + end_cpu.system) - (start_cpu.user + start_cpu.system)) / passes * 1000

    size_kb = os.path.getsize(out_path) / 1024

    return {
        'write_ms': np.mean(write_times),
        'total_cpu_ms': cpu_ms,
        'size_kb': size_kb
    }
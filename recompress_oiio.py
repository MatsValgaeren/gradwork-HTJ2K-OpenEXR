import numpy as np
import OpenImageIO as oiio
import time
import os
import psutil

def recompress(in_path, out_path, compression='none', passes=1):
    out_path = str(out_path)
    buf = oiio.ImageBuf(in_path)

    spec = buf.spec().copy()
    spec.attribute('compression', compression)

    pixels = buf.get_pixels(buf.spec().format)

    process = psutil.Process()
    start_cpu = process.cpu_times()

    write_times = []

    out = oiio.ImageOutput.create(out_path)
    out.open(out_path, spec)

    for _ in range(passes):
        out = oiio.ImageOutput.create(out_path)
        out.open(out_path, spec)

        s_write = time.perf_counter()
        ok = out.write_image(pixels)
        e_write = time.perf_counter()
        out.close()

        if ok:
            write_times.append((e_write - s_write) * 1000)

    end_cpu = process.cpu_times()
    cpu_ms = ((end_cpu.user + end_cpu.system) -
              (start_cpu.user + start_cpu.system)) / max(passes, 1) * 1000

    mean_write_ms = np.mean(write_times) if write_times else float('nan')

    return {
        'compress_write_ms': mean_write_ms,  # total wall time
        'write_ms': mean_write_ms,
        'total_cpu_ms': cpu_ms,
        'wall_ms': mean_write_ms,
        'size_kb': os.path.getsize(out_path) / 1024
        if os.path.exists(out_path) else 0
    }
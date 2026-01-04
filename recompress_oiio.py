import os

os.environ['OIIO_TMPDIR'] = ':ram:'  # RAM-only (run BEFORE import oiio)
os.environ['OIIO_CACHE_PATH'] = ''   # Disable disk cache

import OpenImageIO as oiio
import time
import numpy as np
import psutil


def recompress(in_path, out_path, comp='none', num_threads=1, passes=1):
    process = psutil.Process()
    start_cpu = process.cpu_times()
    write_times = []

    buf = oiio.ImageBuf(in_path)
    spec = buf.spec()  # Copy spec
    spec.attribute("compression", comp)

    for _ in range(passes):
        s_write = time.perf_counter()

        # SIMPLEST: Just write - compression via filename or defaults
        buf.write(out_path)

        spec.attribute("compression", comp)
        e_write = time.perf_counter()

        if os.path.exists(out_path):
            write_times.append((e_write - s_write) * 1000)

    print(f"Wrote {os.path.getsize(out_path) / 1024:.1f}KB")

    end_cpu = process.cpu_times()
    cpu_ms = ((end_cpu.user + end_cpu.system) - (start_cpu.user + start_cpu.system)) / passes * 1000
    size_kb = os.path.getsize(out_path) / 1024

    return {
        'write_ms': np.mean(write_times),
        'total_cpu_ms': cpu_ms,
        'size_kb': size_kb
    }


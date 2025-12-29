import numpy as np
import OpenImageIO as oiio
import time
import os
import psutil

import subprocess

def recompress(in_path, out_path, comp='none', num_threads=1, passes=1):
    # out_path = str(out_path)
    # buf = oiio.ImageBuf(in_path)
    #
    # spec = buf.spec().copy()
    # spec['compression'] = comp
    # spec['nthreads'] = num_threads

    # if not buf.has_error :
    #     buf.write(in_path, format)

    # img = oiio.ImageBuf(in_path)
    # img.specmod().attribute("compression", comp)
    # write_image(img, out_path)
    #
    # return out_path


    process = psutil.Process()
    start_cpu = process.cpu_times()
    #
    write_times = []
    #
    # out = oiio.ImageOutput.create(out_path)
    # out.open(out_path, spec)

    for _ in range(passes):
        # out = oiio.ImageOutput.create(out_path)
        # out.open(out_path, spec)

        s_write = time.perf_counter()
        print(in_path, out_path)

        cmd = [
            'oiiotool',
            in_path,
            f'--compression', comp,
            # f'-threads:{num_threads}',
            '-o', out_path
        ]
        print(cmd)
        result = subprocess.run(cmd, capture_output=True, text=True)

        # ok = out.write_image(pixels)
        e_write = time.perf_counter()
        # out.close()

        if result.returncode == 0 and os.path.exists(out_path):
            write_times.append((e_write - s_write) * 1000)
            print(f"✅ Wrote {os.path.getsize(out_path) / 1024:.1f}KB")

    end_cpu = process.cpu_times()
    cpu_ms = ((end_cpu.user + end_cpu.system) -
              (start_cpu.user + start_cpu.system)) / max(passes, 1) * 1000

    return {
        'write_ms': np.mean(write_times),
        'total_cpu_ms': cpu_ms,
        'size_kb': os.path.getsize(out_path) / 1024
        if os.path.exists(out_path) else 0
    }
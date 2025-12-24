import numpy as np
import OpenImageIO as oiio
import time
import os

def recompress(in_path, out_path, compression='none', passes=1):
    out_path = str(out_path)

    buf = oiio.ImageBuf(in_path)

    spec = buf.spec().copy()
    spec.attribute('compression', compression)

    pixels = buf.get_pixels(buf.spec().format)

    # results = {'compress': [], 'write': []}
    times = []

    for _ in range(passes):
        out = oiio.ImageOutput.create(out_path)
        out.open(out_path, spec)

        # s_compress = time.perf_counter()
        # compressed_buf = oiio.ImageBufAlgo.compression(pixels, compression)
        # e_compress = time.perf_counter()
        # time_to_compress = e_compress - s_compress

        s_write = time.perf_counter()
        out.write_image(pixels)
        e_write = time.perf_counter()

        out.close()
        # results['compress'].append((e_compress - s_compress) * 1000)  # ms
        times.append((e_write - s_write) * 1000)
        # results['write'].append()  # ms


    return {
        'compress_write_ms': np.mean(times),
        # 'write_ms': np.mean(results['write']),
        'std_ms': np.std(times),
        'size_kb': os.path.getsize(out_path) / 1024
    }
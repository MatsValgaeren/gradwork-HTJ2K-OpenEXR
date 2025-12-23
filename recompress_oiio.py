import numpy as np
import OpenImageIO as oiio

def recompress(in_path, out_path, compression='none'):
    in_path = str(in_path)
    out_path = str(out_path)

    buf = oiio.ImageBuf(in_path)

    spec = buf.spec().copy()
    spec.attribute('compression', compression)

    pixels = np.array(buf.get_pixels())
    arr = np.array(pixels, copy=True)

    out = oiio.ImageOutput.create(out_path)
    if out:
        out.open(out_path, spec)
        out.write_image(pixels)
        out.close()

    return True
import os

import OpenEXR
import OpenImageIO as oiio

in_image_dir = "./../source"
out_image_dir = "./images"

def recompress_with_oiio(in_path, out_path, compression='none'):
    in_path = str(in_path)
    out_path = str(out_path)

    buf = oiio.ImageBuf(in_path)

    spec = buf.spec().copy()
    spec.attribute('compression', compression)

    out = oiio.ImageOutput.create(out_path)

    pixels = buf.get_pixels()

    ok = out.write_image(pixels)
    out.close()

    return True


for root, dirs, files in os.walk(in_image_dir):
    for filename in files:
        if filename.endswith(".exr"):

            old_file_path = os.path.join(root, filename)
            new_file_path = os.path.join(out_image_dir, filename[:-4] + "_NOCOMP" + ".exr")
            print(old_file_path, new_file_path)
            try:
                recompress_with_oiio(old_file_path, new_file_path, compression='none')
            except Exception as e:
                print('skipping file: ', e)
import os

import recompress_oiio

in_image_dir = "./../source"
out_image_dir = "./images"

for root, dirs, files in os.walk(in_image_dir):
    for filename in files:
        if filename.endswith(".exr"):

            old_file_path = os.path.join(root, filename)
            new_file_path = os.path.join(out_image_dir, filename[:-4] + "_NO" + ".exr")
            print(old_file_path, new_file_path)
            try:
                recompress_oiio.recompress(old_file_path, new_file_path, compression='none', passes=1)
            except Exception as e:
                print('skipping file: ', e)
import os

import recompress_oiio

in_image_dir = "./../source"
out_image_dir = "./images"

for root, dirs, files in os.walk(in_image_dir):
    for filename in files:
        if filename.endswith(".exr"):
            rel_path = os.path.relpath(root, in_image_dir)

            folder_path = os.path.join(out_image_dir, rel_path)
            os.makedirs(folder_path, exist_ok=True)

            old_file_path = os.path.join(root, filename)
            new_file_path = os.path.join(folder_path, filename[:-4] + "_NO" + ".exr")
            print(new_file_path)
            try:
                recompress_oiio.recompress(old_file_path, new_file_path, comp='none', num_threads=1, passes=1)
            except Exception as e:
                print('skipping file: ', e)
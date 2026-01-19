import os
import recompress_oiio

in_image_dir = "./../source"
out_image_dir = "./out"

def clean(in_dir, out_dir):
    for root, dirs, files in os.walk(in_dir):
        for filename in files:
            print(filename)
            if filename.endswith(".exr") or filename.endswith(".EXR"):
                rel_path = os.path.relpath(root, in_dir)

                folder_path = os.path.join(out_dir, rel_path)
                os.makedirs(folder_path, exist_ok=True)

                old_file_path = os.path.join(root, filename)
                new_file_path = os.path.join(folder_path, filename[:-4] + "_NO.exr")

                try:
                    recompress_oiio.recompress(old_file_path, new_file_path, comp='none', scanline=True, passes=1)
                except Exception as e:
                    print('skipping file: ', e)

# clean(in_image_dir, out_image_dir)
# clean(render_img_dir, out_image_dir)
clean(in_image_dir, out_image_dir)
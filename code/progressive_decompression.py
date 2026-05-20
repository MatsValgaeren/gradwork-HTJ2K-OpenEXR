import time
import os
import OpenImageIO as oiio

import math

IMG_DIR = r"C:\Users\matsv\Desktop\gw\scripts\temp"  # ← DIRECTORY with EXRs
HTJ2K_FILES = [
    r"C:\Users\matsv\Desktop\gw\scripts\temp\render_001.v001.1005_HTJ2K32.exr",
    r"C:\Users\matsv\Desktop\gw\scripts\temp\render_002.v001_HTJ2K32.exr",
    r"C:\Users\matsv\Desktop\gw\scripts\temp\render_003.v001_HTJ2K32.exr"
    ]
ZIP_FILES = [
    r"C:\Users\matsv\Desktop\gw\scripts\temp\render_001.v001.1005_ZIP.exr",
    r"C:\Users\matsv\Desktop\gw\scripts\temp\render_002.v001_ZIP.exr",
    r"C:\Users\matsv\Desktop\gw\scripts\temp\render_003.v001_ZIP.exr"
    ]


def test_progressive_timing(image_files, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    timings = {}

    for img in image_files:
        input_img = oiio.ImageInput.open(img)
        if not input_img:
            print("Failed to open image!")
            return
        spec = input_img.spec()
        pixels = input_img.read_image("float")
        input_img.close()

        height, width = spec.height, spec.width
        print(f"Original: {width}x{height}")

        for quality_pct in [25, 50, 100]:
            scale = {25: 0.25, 50: 0.5, 100: 1.0}[quality_pct]
            step = int(1 / scale)  # 4, 2, 1
            w_small, h_small = width // step, height // step

            # FIXED downsampling
            pixels_small = pixels[::step, ::step, :3]  # Height, Width, Channels

            # Save
            temp_file = os.path.join(output_dir, f"layer_{quality_pct}.exr")
            out_img = oiio.ImageOutput.create(temp_file)
            out_spec = oiio.ImageSpec(w_small, h_small, 3, "float")
            out_img.open(temp_file, out_spec)
            out_img.write_image(pixels_small)
            out_img.close()

            # Time decode
            decode_start = time.perf_counter()
            test_img = oiio.ImageInput.open(temp_file)
            test_pixels = test_img.read_image("float")
            test_img.close()
            decode_time = (time.perf_counter() - decode_start) * 1000

            timings[quality_pct] = decode_time


            # frames = round(decode_time / 2 * 24, 0)
            #
            #
            # print(f"Layer {quality_pct}%: {decode_time:.1f}ms ({w_small}x{h_small})")
            # print(frames, 'frames')

    return timings


# Run with SINGLE FILE
HTJ2K_timings = test_progressive_timing(HTJ2K_FILES, r"C:\Users\matsv\Desktop\gw\scripts\prog_out")
ZIP_timings = test_progressive_timing(ZIP_FILES, r"C:\Users\matsv\Desktop\gw\scripts\prog_out")
print("\nDemo timings:", HTJ2K_timings, '\n', ZIP_timings)

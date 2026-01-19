import os
import OpenImageIO as oiio
import time

os.environ['OIIO_TMPDIR'] = ':ram:'
os.environ['OIIO_CACHE_PATH'] = ''

input_dir = r'E:\gw\test'
out_dir = r'E:\gw\temp'

compression_map = {
    'RLE_COMPRESSION': 'rle',
    'ZIP_COMPRESSION': 'zip',
    'PIZ_COMPRESSION': 'piz',
    'ZIPS_COMPRESSION': 'zips',
    'HTJ2K32_COMPRESSION': 'htj2k:32',
    'HTJ2K256_COMPRESSION': 'htj2k:256'
}

PASSES = 1

def go_over_compression():
    for compression in compression_map:
        oiio_comp = compression_map[compression]
        comp_short = compression.split("_")[0]

        for root, dirs, files in os.walk(input_dir):
            no_files = [f for f in files if f.endswith('_NO.exr')]

            for filename in no_files:
                old_file_path = os.path.join(root, filename)
                base_name = filename[:-7]

                output_folder = os.path.join(out_dir, compression, base_name[:-5])
                os.makedirs(output_folder, exist_ok=True)


                new_file_path = os.path.join(output_folder, f"{base_name}_{comp_short}.exr")

                recompress_1080p_nuke(
                    old_file_path, new_file_path,
                    comp=oiio_comp
                )

def recompress_1080p_nuke(in_path, out_path, comp='none', scanline=True):
    src_buf = oiio.ImageBuf(in_path)

    # Resize to 1080p
    new_spec = oiio.ImageSpec(1920, 1080, src_buf.spec().nchannels, src_buf.spec().format)
    new_spec.attribute("compression", comp)  # Set compression

    if scanline:
        new_spec.tile_width = new_spec.tile_height = new_spec.tile_depth = 0
    else:
        new_spec.tile_width = new_spec.tile_height = 64
        new_spec.tile_depth = 1

    resized_buf = oiio.ImageBuf(new_spec)
    oiio.ImageBufAlgo.resize(resized_buf, src_buf)

    resized_buf.write(out_path)

    print(f"Wrote 1080p {comp}: {os.path.getsize(out_path) / 1024 / 1024:.1f} MB")

def recomp():
    total_start = time.perf_counter()
    go_over_compression()

    elapsed = time.perf_counter() - total_start

    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)

    print(f"{int(hours)}h {int(minutes)}m {seconds:.2f}s")





recomp()
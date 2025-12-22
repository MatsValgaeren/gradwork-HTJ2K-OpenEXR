import os

import OpenEXR

print('starting')

def compression_name(path):
    f = OpenEXR.InputFile(path)
    comp = f.header()['compression']
    # Map known OpenEXR constants to readable names
    comp_map = {
        OpenEXR.NO_COMPRESSION: "NO_COMPRESSION",
        OpenEXR.RLE_COMPRESSION: "RLE_COMPRESSION",
        OpenEXR.ZIPS_COMPRESSION: "ZIPS_COMPRESSION",
        OpenEXR.ZIP_COMPRESSION: "ZIP_COMPRESSION",
        OpenEXR.PIZ_COMPRESSION: "PIZ_COMPRESSION",
        OpenEXR.PXR24_COMPRESSION: "PXR24_COMPRESSION",
        OpenEXR.B44_COMPRESSION: "B44_COMPRESSION",
        OpenEXR.B44A_COMPRESSION: "B44A_COMPRESSION",
        OpenEXR.DWAA_COMPRESSION: "DWAA_COMPRESSION",
        OpenEXR.DWAB_COMPRESSION: "DWAB_COMPRESSION",
    }
    print(comp)

image_dir = "./images"

for root, dirs, files in os.walk(image_dir):
    for filename in files:
        file_path = os.path.join(root, filename)

        if file_path.endswith(".exr"):
            print(file_path)
            compression_name(file_path)
print('ended')



# with OpenEXR.File("image.exr") as infile:
#
#     header = infile.header()
#     print(f"type={header['type']}")
#     print(f"compression={header['compression']}")
#
#     RGB = infile.channels()["RGB"].pixels
#     height, width = RGB.shape[0:2]
#     for y in range(height):
#         for x in range(width):
#             pixel = (RGB[y, x, 0], RGB[y, x, 1], RGB[y, x, 2])
#             print(f"pixel[{y}][{x}]={pixel}")
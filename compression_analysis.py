import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np

result_dir = "./results"

COMPRESSION_METHODS = {
    "NO_COMPRESSION",
    "RLE_COMPRESSION",
    "ZIPS_COMPRESSION",
    "ZIP_COMPRESSION",
    "PIZ_COMPRESSION",
    "PXR24_COMPRESSION",
    "B44_COMPRESSION",
    "B44A_COMPRESSION",
    "DWAA_COMPRESSION",
    "DWAB_COMPRESSION",
    "HTJ2K256_COMPRESSION",
    "HTJ2K32_COMPRESSION"
}

analysed = {m: {"count": 0, "total_dur": 0, "total_read_duration": 0, "avg_read_duration": 0, "total_write_duration": 0, "avg_write_duration": 0, "total_file_size": 0, "avg_file_size": 0} for m in COMPRESSION_METHODS}

def print_results():
    for item in analysed:
        analysed[item]["avg_read_duration"] = analysed[item]["total_read_duration"] / analysed[item]["count"] * 100
        analysed[item]["avg_write_duration"] = analysed[item]["total_write_duration"] / analysed[item]["count"] * 100
        analysed[item]["avg_file_size"] = analysed[item]["total_file_size"] / analysed[item]["count"] / 1024 / 1024
        print(item, 'avg read time of', analysed[item]["avg_read_duration"], 'milliseconds')
        print(item, 'avg compression time of', analysed[item]["avg_write_duration"], 'milliseconds')
        print(item, 'avg file size of', analysed[item]["avg_file_size"], 'kb')

def plot_results():
    x = []
    y = []
    z = []
    labels = []

    font = {'color': 'black',
            'weight': 'bold',
            'size': 5
            }

    for comp in analysed:
        x.append(analysed[comp]["avg_write_duration"])
        z.append(analysed[comp]["total_file_size"])
        y.append(analysed[comp]["avg_read_duration"])
        labels.append(comp.replace('_COMPRESSION', ''))


    x = np.array(x)
    y = np.array(y)
    z = np.array(z)

    # Publication styling
    plt.rcParams.update({'font.size': 10, 'savefig.dpi': 300})
    plt.figure(figsize=(10, 8))

    scatter = plt.scatter(x, y, s=100, alpha=0.7, c=z, edgecolors='black')

    # Smart labels (avoid overlap)
    for i, label in enumerate(labels):
        plt.annotate(label, (x[i], y[i]), xytext=(1, 1), textcoords='offset points',
                     fontsize=8, ha='left', fontweight='bold')

    plt.xlabel('Write Time (ms)', fontsize=12, fontweight='bold')
    plt.ylabel('File Size (KB)', fontsize=12, fontweight='bold')
    plt.title('OpenEXR Compression: Write Time vs File Size', fontsize=14,
              fontweight='bold')

    plt.grid(True, alpha=0.3)
    plt.colorbar(scatter, label='Read Time (ms)')

    # plt.tight_layout()
    # plt.savefig('exr_benchmark.pdf', bbox_inches='tight', dpi=300)  # Publication ready
    plt.show()


def analyse(dir):
    for root, dirs, files in os.walk(dir):
        for filename in files:
            print('start')
            file_path = os.path.join(root, filename)
            print('filepath ', file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                for item in json_data:
                    comp = item['compression']
                    curr_read_duration = item['read_duration']
                    curr_write_duration = item['write_duration']
                    curr_file_size = item['file_size']

                    analysed[comp]["total_read_duration"] += curr_read_duration
                    analysed[comp]["total_write_duration"] += curr_write_duration
                    analysed[comp]["total_file_size"] += curr_file_size
                    analysed[comp]["count"] += 1

    print_results()
    plot_results()


analyse(result_dir)
print(analysed)
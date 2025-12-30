import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

result_dir = "./results"

COMPRESSION_METHODS = [
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
]

colors = sns.color_palette("husl", 12)

METHOD_COLOR_MAP = {}
for i, method in enumerate(COMPRESSION_METHODS):
    METHOD_COLOR_MAP[method] = colors[i]

image_mapping = {
    # === UNUSUAL PIXEL IMAGES (edge cases, NaNs, extremes) ===
    'AllHalfValues': 'Unusual Pixels',
    'BrightRings': 'Unusual Pixels',
    'BrightRingsNanInf': 'Unusual Pixels',
    'GammaChart': 'Unusual Pixels',
    'GrayRampsDiagonal': 'Unusual Pixels',
    'GrayRampsHorizontal': 'Unusual Pixels',
    'RgbRampsDiagonal': 'Unusual Pixels',
    'SquaresSwirls': 'Unusual Pixels',
    'WideColorGamut': 'Unusual Pixels',
    'WideFloatRange': 'Unusual Pixels',

    # === SCANLINE IMAGES (traditional VFX plates) ===
    'Blobbies': 'Scanline',
    'CandleGlass': 'Scanline',
    'Cannon': 'Scanline',
    'Carrots': 'Scanline',
    'Desk': 'Scanline',
    'MtTamWest': 'Scanline',
    'PrismsLenses': 'Scanline',
    'StillLife': 'Scanline',
    'Tree': 'Scanline',

    # === TILED IMAGES (progressive/HTJ2K optimized) ===
    'GoldenGate': 'Tiled',
    'Ocean': 'Tiled',
    'Spirals': 'Tiled',

    # === CHROMATICITIES (color space tests) ===
    'Rec709': 'Chromaticities',
    'Rec709_YC': 'Chromaticities',
    'XYZ': 'Chromaticities',
    'XYZ_YC': 'Chromaticities',

    # === LUMINANCE/CHROMA IMAGES ===
    'CrissyField': 'LuminanceChroma',
    'Flowers': 'LuminanceChroma',
    'Garden': 'LuminanceChroma',
    'MtTamNorth': 'LuminanceChroma',
    'StarField': 'LuminanceChroma',

    # === MULTIPART / MULTIVIEW BEACHBALL (stereo, complex AOVs) ===
    'multipart.0001': 'MultiPart',
    'multipart.0002': 'MultiPart',
    'multipart.0003': 'MultiPart',
    'multipart.0004': 'MultiPart',
    'multipart.0005': 'MultiPart',
    'multipart.0006': 'MultiPart',
    'multipart.0007': 'MultiPart',
    'multipart.0008': 'MultiPart',
    'singlepart.0001': 'MultiPart',
    'singlepart.0002': 'MultiPart',
    'singlepart.0003': 'MultiPart',
    'singlepart.0004': 'MultiPart',
    'singlepart.0005': 'MultiPart',
    'singlepart.0006': 'MultiPart',
    'singlepart.0007': 'MultiPart',
    'singlepart.0008': 'MultiPart',

    # === MULTI-VIEW IMAGES (stereo pairs) ===
    'Adjuster': 'MultiView',
    'Balls': 'MultiView',
    'Fog': 'MultiView',
    'Impact': 'MultiView',
    'LosPadres': 'MultiView',

    # === MULTI-RESOLUTION (mipmaps, env maps) ===
    'Bonita': 'MultiResolution',
    'ColorCodedLevels': 'MultiResolution',
    'Kapaa': 'MultiResolution',
    'KernerEnvCube': 'MultiResolution',
    'KernerEnvLatLong': 'MultiResolution',
    'MirrorPattern': 'MultiResolution',
    'OrientationCube': 'MultiResolution',
    'OrientationLatLong': 'MultiResolution',
    'PeriodicPattern': 'MultiResolution',
    'StageEnvCube': 'MultiResolution',
    'StageEnvLatLong': 'MultiResolution',
    'WavyLinesCube': 'MultiResolution',
    'WavyLinesLatLong': 'MultiResolution',
    'WavyLinesSphere': 'MultiResolution',

    # === STEREO / DEEP IMAGES ===
    'v2/Stereo/Balls': 'StereoDeep',
    'v2/Stereo/Ground': 'StereoDeep',
    'v2/Stereo/Leaves': 'StereoDeep',
    'v2/Stereo/Trunks': 'StereoDeep',
    'v2/Stereo/composited': 'StereoDeep',
    'v2/LeftView/Balls': 'StereoLeft',
    'v2/LeftView/Ground': 'StereoLeft',
    'v2/LeftView/Leaves': 'StereoLeft',
    'v2/LeftView/Trunks': 'StereoLeft',
    'v2/LowResLeftView/Balls': 'StereoLowRes',
    'v2/LowResLeftView/Ground': 'StereoLowRes',
    'v2/LowResLeftView/Leaves': 'StereoLowRes',
    'v2/LowResLeftView/Trunks': 'StereoLowRes',
    'v2/LowResLeftView/composited': 'StereoLowRes'
}

analysed = {m: {"count": 0, "total_dur": 0, "total_read_duration": 0, "avg_read_duration": 0, "total_write_duration": 0, "avg_write_duration": 0, "total_wall_duration": 0, "avg_wall_duration": 0, "total_file_size": 0, "avg_file_size": 0, "max_cpu": 0, "max_ram": 0} for m in COMPRESSION_METHODS}

def print_results():
    for item in analysed:
        analysed[item]["avg_read_duration"] = analysed[item]["total_read_duration"] / analysed[item]["count"] * 100
        analysed[item]["avg_write_duration"] = analysed[item]["total_write_duration"] / analysed[item]["count"] * 100
        analysed[item]["avg_file_size"] = analysed[item]["total_file_size"] / analysed[item]["count"] / 1024 / 1024
        print(item, 'avg read time of', analysed[item]["avg_read_duration"], 'milliseconds')
        print(item, 'avg compression time of', analysed[item]["avg_write_duration"], 'milliseconds')
        print(item, 'avg file size of', analysed[item]["avg_file_size"], 'kb')
        print(item, 'max cpu', analysed[item]["max_cpu"], 'milliseconds')

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
        x.append(analysed[comp]["avg_read_duration"])
        z.append(analysed[comp]["avg_write_duration"])
        y.append(analysed[comp]["total_file_size"])
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

def plot_cores(avg_stats, stat):
    method_labels = avg_stats['method'].unique()
    # method_labels = COMPRESSION_METHODS
    core_labels = sorted(avg_stats['cores'].unique())

    cores_to_plot = [1, 16]

    new_avg = avg_stats.groupby(['cores', 'method'], as_index=False).agg({
        'read_ms': 'mean',
        'write_ms': 'mean',
        'size_kb': 'mean',
        'cpu_ms': 'mean'
    }).round(2)

    pivot_data = new_avg.pivot(index='method', columns='cores', values=stat)

    x = range(len(pivot_data))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 8))

    ax.bar([i - width / 2 for i in x], pivot_data[cores_to_plot[0]],
           width, label=f'{cores_to_plot[0]} Core vs ' + stat, alpha=0.8)

    if len(cores_to_plot) > 1:
        ax.bar([i + width / 2 for i in x], pivot_data[cores_to_plot[1]],
               width, label=f'{cores_to_plot[1]} Core vs ' + stat, alpha=0.8)

    plt.title(stat + ' VS Cores')

    # plt.xlabel('Number of Threads')
    plt.ylabel('Cores')

    ax.set_xticks(x)
    ax.set_xticklabels([m.split('_')[0] for m in method_labels], rotation=45)
    print('show')
    plt.show()

from scipy.stats import friedmanchisquare
import scikit_posthocs as sp

def plot_unique_groups(avg_stats, unique_groups):
    n_groups = len(unique_groups)

    fig, axes = plt.subplots(n_groups, 1, figsize=(12, 4 * n_groups))

    for i, img_group in enumerate(unique_groups):
        curr_df = avg_stats[
            (avg_stats['image_group'] == img_group) &
            avg_stats['cores'].isin(avg_stats['cores'].unique())
            ]

        colors = [METHOD_COLOR_MAP[method] for method in curr_df['method']]
        axes[i].scatter(curr_df['read_ms'], curr_df['size_kb'],
                        c = colors,
                        alpha=0.8, edgecolors='black', linewidth=2,
                        s=100)

        for j, row in avg_stats.iterrows():
            axes[i].annotate(f"{(row['method'].split('_')[0])}",
                            (row['read_ms'], row['size_kb']),
                            xytext=(5, 5), textcoords='offset points',
                            fontsize=6, fontweight='bold', ha='left')

        axes[i].set_xlabel('Read Time (ms)')
        axes[i].set_ylabel('Size (KB)')
        axes[i].set_title(f'{img_group} - Read Time vs Size')

    plt.tight_layout()
    plt.show()

def friedman_test(df, metric, cores, machine=None):
    # Filter to one condition
    sub = df[df['cores'] == cores].copy()
    if machine is not None:
        sub = sub[sub['machine'] == machine]

    # Average repeated runs per image/method
    sub = (
        sub.groupby(['file', 'method'])[metric]
        .mean()
        .reset_index()
    )

    # Pivot to image × method
    pivot = sub.pivot(index='file', columns='method', values=metric)

    # Drop images missing any method
    pivot = pivot.dropna()

    print(f"Images used: {pivot.shape[0]}")
    print(f"Methods: {pivot.shape[1]}")

    # Friedman test
    stat, p = friedmanchisquare(*[pivot[col] for col in pivot.columns])

    return stat, p, pivot

def analyse(dir_path):
    plt.style.use('seaborn-v0_8-paper')

    all_data = []

    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            if filename.endswith('.json'):
                file_path = os.path.join(root, filename)
                try:
                    df = pd.read_json(file_path)
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    df = pd.concat(all_data, ignore_index=True)

    # exclude_methods = ['NO_COMPRESSION', 'RLE_COMPRESSION', 'DWAA_COMPRESSION', 'DWAB_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION', 'PIZ_COMPRESSION']
    # df = df[~df['method'].isin(exclude_methods)]

    df['image_group'] = df['file'].map(image_mapping).fillna('Other')

    avg_stats = df.groupby(['cores', 'method', 'image_group'], as_index=False).agg({
        'read_ms': 'mean',
        'write_ms': 'mean',
        'size_kb': 'mean',
        'cpu_ms': 'mean'
    }).round(2)

    print("Summary Statistics:")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
        print(avg_stats.sort_values(['image_group', 'size_kb'], ascending=True))

    # metrics = ['read_ms', 'write_ms', 'size_kb', 'cpu_ms']
    # fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    # axes = axes.flatten()
    #
    # for i, metric in enumerate(metrics):
    #     sns.violinplot(data=df, x='image_group', y=metric, hue='method',
    #                    split=True, inner='quart', ax=axes[i])
    #     axes[i].set_title(f'{metric.replace("_", " ").title()} by Image Group & Method')
    #     axes[i].tick_params(axis='x', rotation=45)
    #
    # plt.tight_layout()
    # plt.savefig('compression_violins.png', dpi=300, bbox_inches='tight')
    # plt.show()

    stat, p, pivot_size = friedman_test(df, metric='size_kb', cores=16)
    print(f"Friedman χ² = {stat:.3f}, p = {p:.3e}")
    mean_size_ranks = pivot_size.rank(axis=1, method='average').mean()


    stat, p, pivot_read = friedman_test(df, metric='read_ms', cores=16)
    print(f"Friedman χ² = {stat:.3f}, p = {p:.3e}")
    mean_read_ranks = pivot_read.rank(axis=1, method='average').mean()

    stat, p, write_write = friedman_test(df, metric='write_ms', cores=16)
    print(f"Friedman χ² = {stat:.3f}, p = {p:.3e}")
    mean_write_ranks = write_write.rank(axis=1, method='average').mean()

    rank_table = pd.concat(
        {
            'size': mean_size_ranks,
            'read': mean_read_ranks,
            'write': mean_write_ranks,
        },
        axis=1
    )
    rank_table = rank_table.sort_values(by='size')
    print(rank_table)

    return

    unique_groups = avg_stats['image_group'].unique()

    plt.rcParams.update({'font.size': 12, 'savefig.dpi': 300})



    plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups)
    plot_unique_groups(avg_stats[avg_stats['cores'] == 16], unique_groups)
    plot_cores(avg_stats, 'read_ms')
    plot_cores(avg_stats, 'write_ms')
    plot_cores(avg_stats, 'size_kb')




analyse(result_dir)
# print(analysed)
import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from scipy.stats import friedmanchisquare

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
    'v2/LowResLeftView/composited': 'StereoLowRes',

    'render_001.v001.1005': 'Blender',
    'render_002.v001': 'Blender',
    'render_003.v001': 'Blender'
}

def plot_cores(avg_stats, stat):
    method_labels = avg_stats['method'].unique()
    # method_labels = COMPRESSION_METHODS
    core_labels = sorted(avg_stats['cores'].unique())
    print('lebel', core_labels)
    cores_to_plot = [1, 16]

    pivot_data = avg_stats.pivot(index='method', columns='cores', values=stat)

    x = range(len(pivot_data))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 8))

    ax.bar([i - width / 2 for i in x], pivot_data[cores_to_plot[0]],
           width, label=f'{cores_to_plot[0]} Core vs ' + stat, alpha=0.8)

    if len(cores_to_plot) > 1:
        ax.bar([i + width / 2 for i in x], pivot_data[cores_to_plot[1]],
               width, label=f'{cores_to_plot[1]} Core vs ' + stat, alpha=0.8)

    plt.title(stat + ' VS Cores')

    plt.ylabel('Cores')

    ax.set_xticks(x)
    ax.set_xticklabels([m.split('_')[0] for m in method_labels], rotation=45)
    plt.show()


def plot_unique_groups(avg_stats, unique_groups, xs, ys):
    n_groups = len(unique_groups)

    fig, axes = plt.subplots(n_groups, 1, figsize=(12, 4 * n_groups))

    for i, img_group in enumerate(unique_groups):
        curr_df = avg_stats[
            (avg_stats['image_group'] == img_group) &
            avg_stats['cores'].isin(avg_stats['cores'].unique())
            ]

        colors = [METHOD_COLOR_MAP[method] for method in curr_df['method']]
        axes[i].scatter(curr_df[xs], curr_df[ys],
                        c = colors,
                        alpha=0.8, edgecolors='black', linewidth=2,
                        s=100)

        for j, row in curr_df.iterrows():  # Only current group rows
            method_short = row['method'].split('_')[0]
            axes[i].annotate(method_short,
                             (row[xs], row[ys]),
                             xytext=(5, 5), textcoords='offset points',
                             fontsize=7, fontweight='bold', ha='left')

        axes[i].set_xlabel(xs)
        axes[i].set_ylabel(ys)
        axes[i].set_title(f'{img_group} - {xs} vs {ys}')

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

    pivot = sub.pivot(index='file', columns='method', values=metric)
    pivot = pivot.dropna()

    print(f"Images used: {pivot.shape[0]}")
    print(f"Methods: {pivot.shape[1]}")

    if pivot.shape[1] < 3:
        return 0, 1.0, pivot
    # Friedman test
    stat, p = friedmanchisquare(*[pivot[col] for col in pivot.columns])

    return stat, p, pivot

def friedman_analysis(df, metrics, cores, machine=None):
    pivots = {}
    mean_ranks = {}

    for metric in metrics:
        stat, p, pivot = friedman_test(df, metric=metric, cores=cores, machine=machine)
        print(f"Friedman χ² = {stat:.3f}, p = {p:.3e}")
        mean_ranks[metric] = pivot.rank(axis=1, method='average').mean()
        pivots[metric] = pivot

    rank_table = pd.concat(mean_ranks, axis=1)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.expand_frame_repr', False)

    print("\nRank Table (lower = better):")
    print(rank_table)

    return rank_table, pivots

def load_data(dir_path):
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

    return df

def analyse(dir_path):
    plt.style.use('seaborn-v0_8-paper')
    df = load_data(dir_path)

    # exclude_methods = ['NO_COMPRESSION', 'DWAA_COMPRESSION', 'DWAB_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION', 'PXR24_COMPRESSION', 'RLE_COMPRESSION']
    # df = df[~df['method'].isin(exclude_methods)]

    df['image_group'] = df['file'].map(image_mapping).fillna('Other')

    # "ROI": {
    #     "ROI_0%-100%": 4.87,
    #     "ROI_10%-40%": 0.9,
    #     "ROI_40%-60%": 0.16,
    #     "ROI_0%-50%": 1.38
    # }

    df['ROI_full'] = df['ROI'].apply(lambda x: x.get('ROI_0%-100%', 0))
    df['ROI_tiny'] = df['ROI'].apply(lambda x: x.get('ROI_10%-40%', 0))
    df['ROI_small'] = df['ROI'].apply(lambda x: x.get('ROI_40%-60%', 0))
    df['ROI_half'] = df['ROI'].apply(lambda x: x.get('ROI_0%-50%', 0))

    avg_stats = df.groupby(['cores', 'method', 'image_group'], as_index=False).agg({
        'read_ms': 'mean', 'write_ms': 'mean', 'size_kb': 'mean',
        'cpu_ms': 'mean', 'ram_usage': 'mean',
        'ROI_full': 'mean',
        'ROI_half': 'mean',
        'ROI_small': 'mean',
        'ROI_tiny': 'mean'
    }).round(2)


    # print("Summary Statistics:")
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
    #     print(avg_stats.sort_values(['image_group', 'size_kb'], ascending=True))

    priority_groups = [
        'Chromaticities',
        'LuminanceChroma',
        'Scanline',
        'Tiled',
        'MultiResolution',
        'Other',
        'Blender'
    ]

    df_priority = df[df['image_group'].isin(priority_groups)].copy()

    # def friedman_analysis(df, metrics, cores, machine=None):
    friedman_analysis(df_priority, ['size_kb', 'read_ms', 'write_ms', 'ram_usage', 'ROI_full', 'ROI_half', 'ROI_small', 'ROI_tiny'], 1)
    # friedman_analysis(df_priority, ['size_kb', 'read_ms', 'write_ms', 'ram_usage'], 16)

    unique_groups = avg_stats['image_group'].unique()
    plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'ROI_full', 'size_kb')
    plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'read_ms', 'size_kb')
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'write_ms', 'size_kb')
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'ram_usage', 'size_kb')
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 16], unique_groups, 'read_ms', 'size_kb')
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 16], unique_groups, 'write_ms', 'size_kb')

    new_avg = avg_stats.groupby(['cores', 'method'], as_index=False).agg({
        'read_ms': 'mean',
        'write_ms': 'mean',
        'size_kb': 'mean',
        'cpu_ms': 'mean',
        'ram_usage': 'mean',
        'ROI_full': 'mean',
        'ROI_half': 'mean',
        'ROI_small': 'mean',
        'ROI_tiny': 'mean'
    }).round(2)

    # plot_cores(new_avg, 'read_ms')
    # plot_cores(new_avg, 'ROI_full')
    # plot_cores(new_avg, 'ROI_tiny')
    # plot_cores(new_avg, 'write_ms')
    # plot_cores(new_avg, 'ram_usage')
    # plot_cores(new_avg, 'size_kb')


import glob

latest_results = max(glob.glob(result_dir), key=os.path.getctime)

analyse(latest_results)
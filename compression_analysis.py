import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from scipy.stats import friedmanchisquare

result_dir = "./results"
graphs_dir = "./graphs"

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

def plot_cores(avg_stats, stat, save=False):

    method_labels = avg_stats['method'].unique()
    # method_labels = COMPRESSION_METHODS
    core_labels = sorted(avg_stats['cores'].unique())

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

    if save:
        file_name = os.path.join(graphs_dir, f'{stat}_vs_cores.png')
        plt.savefig(file_name)

    plt.show()


def plot_unique_groups(avg_stats, unique_groups, xs, ys, save=False):
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

    if save:
        file_name = os.path.join(graphs_dir, f'image_{xs}_vs_{xs}.png')
        plt.savefig(file_name)

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

def friedman_analysis(df, metrics, cores=1, machine=None):
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
            if not filename.endswith('.json'):
                continue

            file_path = os.path.join(root, filename)

            try:
                with open(file_path) as f:
                    raw = json.load(f)  # List[dict]

                for record in raw:
                    row = {
                        'cores': record.get('cores'),
                        'method': record.get('method'),
                        'file': record.get('file'),
                        # group by base image name
                        'image_group': record.get('file', '').split('.')[0]
                    }

                    # ---- SCAN ----
                    for k, v in record.get('scan', {}).items():
                        if isinstance(v, dict):
                            for rk, rv in v.items():
                                row[f'scan.{k}.{rk}'] = rv
                        else:
                            row[f'scan.{k}'] = v

                    # ---- TILED ----
                    for k, v in record.get('tiled', {}).items():
                        if isinstance(v, dict):
                            for rk, rv in v.items():
                                row[f'tiled.{k}.{rk}'] = rv
                        else:
                            row[f'tiled.{k}'] = v

                    all_data.append(row)

            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    return pd.DataFrame(all_data)

def roi_full_table(df):
    scan_roi = sorted([c for c in df if 'scan.roi_decode_ms.ROI_' in c])
    tile_roi = sorted([c for c in df if 'tiled.roi_decode_ms.ROI_' in c])

    print(f"📊 {len(scan_roi)} ROIs × 12 codecs")
    roi_means = df[['method'] + scan_roi + tile_roi].groupby('method').mean()

    # PRINT ALL COLUMNS
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(roi_means.round(1))
    pd.reset_option('display.max_columns')

    # SPEEDUP SUMMARY
    print("\n⚡ Layout speedup (scan→tiled avg):")
    for roi in scan_roi[:6]:
        s, t = roi_means[roi].mean(), roi_means[roi.replace('scan', 'tiled')].mean()
        print(f"{roi.split('_')[-1]:12} {s:6.1f}ms → {t:6.1f}ms ({s / t:.1f}x)")


def analyse(dir):
    plt.style.use('seaborn-v0_8-paper')
    df = load_data(dir)

    scan_cols = [col for col in df.columns if col.startswith('scan.') and col != 'scan.roi_decode_ms']
    tile_cols = [col for col in df.columns if col.startswith('tiled.') and col != 'tiled.roi_decode_ms']

    agg_dict = dict.fromkeys(scan_cols + tile_cols, 'mean')

    avg_stats = df.groupby(['cores', 'method', 'image_group']).agg(agg_dict).round(2).reset_index()

    safe_metrics = ['read_ms', 'write_ms', 'size_kb'] if 'scan.read_ms' in avg_stats else []
    for m in safe_metrics:
        plot_cores(avg_stats, f'scan.{m}', True)
        plot_cores(avg_stats, f'tiled.{m}', True)

    # ROI SPEEDUP (handles your 0.4x)
    if 'scan.roi_decode_ms.ROI_45%-55%' in df.columns:
        speedup = df['scan.roi_decode_ms.ROI_45%-55%'].mean() / df['tiled.roi_decode_ms.ROI_45%-55%'].mean()
        print(f"Tiny ROI speedup (scan/tiled): {speedup:.1f}x")

    roi_full_table(df)

    metrics = ['size_kb', 'read_ms', 'write_ms', 'ram_usage']

    # ROI COLUMNS (flattened)
    roi_cols = [col for col in df.columns if col.endswith('_decode_ms.ROI_')]
    core_metrics = ['read_ms', 'write_ms', 'size_kb', 'cpu_ms', 'ram_usage']

    exclude_methods = ['NO_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION', 'RLE_COMPRESSION']
    # exclude_methods = ['NO_COMPRESSION', 'DWAA_COMPRESSION', 'DWAB_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION', 'PXR24_COMPRESSION', 'RLE_COMPRESSION']
    # df = df[~df['method'].isin(exclude_methods)]



    # FRIEDMAN SCAN vs TILE SEPARATE
    print("\n=== SCANLINE ===")
    scan_metrics = [f"scan.{m}" for m in core_metrics]
    friedman_analysis(df, scan_metrics, cores=1)

    print("\n=== TILED ===")
    tile_metrics = [f"tiled.{m}" for m in core_metrics]
    friedman_analysis(df, tile_metrics, cores=1)
    #
    # key_rois = ['ROI_0%-100%', 'ROI_45%-55%']  # Full + tiny
    # print("\n=== SCAN ROI ===")
    # friedman_analysis(df, [f"scan.roi_decode_ms.{r}" for r in key_rois], 1)
    # print("\n=== TILED ROI ===")
    # friedman_analysis(df, [f"tiled.roi_decode_ms.{r}" for r in key_rois], 1)




    # PRIORITY GROUPS
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

    # AGGREGATE (drop broken df_roi)
    agg_dict = {f"{l}.{m}": 'mean' for l in ['scan', 'tiled'] for m in core_metrics}
    agg_dict.update({col: 'mean' for col in roi_cols[:4]})  # Top ROIs

    # unique_groups = avg_stats['image_group'].unique()
    # if len(unique_groups) > 0:
    #     plot_unique_groups(avg_stats[avg_stats.cores == 1], unique_groups,
    #                        'scan.read_ms', 'scan.size_kb', True)
    # else:
    #     print("No image_groups for plots")

    # Layout speedup
    df['roi_speedup'] = df['scan.roi_decode_ms.ROI_45%-55%'] / df['tiled.roi_decode_ms.ROI_45%-55%']
    print(f"Tiled ROI speedup (tiny): {df['roi_speedup'].mean():.1f}x")

    # plot_cores(avg_stats, 'scan.read_ms', False)
    # print('ewf')
    # plot_cores(avg_stats, 'scan.write_ms', False)
    # print('ewf')
    # plot_cores(avg_stats, 'scan.ram_usage', False)
    # plot_cores(avg_stats, 'scan.size_kb', False)

    return


    # avg_stats = avg_stats[avg_stats['image_group'].isin(['Scanline', 'Tiled'])]
    # def friedman_analysis(df, metrics, cores, machine=None):
    # friedman_analysis(df_priority, ['size_kb', 'read_ms', 'write_ms', 'ram_usage'], 1)
    # friedman_analysis(df_priority, roi_columns, 1)

    unique_groups = avg_stats['image_group'].unique()
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'ROI_full', 'size_kb', False)
    plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'read_ms', 'size_kb', True)
    plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'write_ms', 'size_kb', True)
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 1], unique_groups, 'ram_usage', 'size_kb', False)
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 16], unique_groups, 'read_ms', 'size_kb', False)
    # plot_unique_groups(avg_stats[avg_stats['cores'] == 16], unique_groups, 'write_ms', 'size_kb', False)

analyse(result_dir)
import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from nooverlap import push_text_free
from adjustText import adjust_text
from pandas.io.sas.sas_constants import text_block_size_length
from matplotlib.ticker import MultipleLocator

from scipy.stats import friedmanchisquare

result_dir = "results"
graphs_dir = "./graphs"

COMPRESSION_METHODS = [
    "NO_COMPRESSION",
    "RLE_COMPRESSION",
    "ZIPS_COMPRESSION",
    "ZIP_COMPRESSION",
    "PIZ_COMPRESSION",
    "HTJ2K32_COMPRESSION",
    "HTJ2K256_COMPRESSION",
    "PXR24_COMPRESSION",
    "B44_COMPRESSION",
    "B44A_COMPRESSION",
    "DWAA_COMPRESSION",
    "DWAB_COMPRESSION"
]

GROUP_CATEGORIES = {
    'CosmosLaundromat': 'Netflix',
    'Meridian': 'Netflix',
    'Sparks': 'Netflix',

    '0010_TestSand_Robot_Comp': 'Geo',
    '0130_Geo_Comp': 'Geo',
    '0160_Geo_Front_Comp': 'Geo',
    '0160_Geo_Back_Comp': 'Geo',


    '0010_TestSand_Sand_Comp': 'Particles',
    '0130_VDB_Comp': 'VDB'
}

colors = [
    '#e41a1c',
    '#377eb8',
    '#4daf4a',
    '#8ECF8C',
    '#984ea3',
    '#ff7f00',
    '#FFAD5C',
    '#ffff33',
    '#a65628',
    '#D68557',
    '#f781bf',
    '#FDE7F3'
]

METHOD_COLOR_MAP = {method: colors[i] for i, method in enumerate(COMPRESSION_METHODS)}


def friedman_analysis(df, metrics, cores=1, exclude_methods=None):
    df_filtered = df.copy()
    if cores != 'all':
        df_filtered = df_filtered[df_filtered['cores'].isin(cores if isinstance(cores, list) else [cores])]

    if exclude_methods:
        df_filtered = df_filtered[~df_filtered['method'].isin(exclude_methods)]

    for metric in metrics:
        scan_metric = f'scan.{metric}'
        tiled_metric = f'tiled.{metric}'

        target_metric = scan_metric if scan_metric in df_filtered.columns else tiled_metric

        print(f"\n=== {target_metric} ===")
        print(f"Rows: {len(df_filtered)}, Non-null: {df_filtered[target_metric].notna().sum()}")

        pivot = df_filtered.pivot_table(
            index='file', columns='method', values=target_metric
        ).dropna()

        print(f"Pivot: {pivot.shape} files × {len(pivot.columns)} methods")

        if len(pivot.columns) < 3:
            continue

        stat, p = friedmanchisquare(*pivot.values)
        print(f"Friedman χ²={stat:.3f}, p={p:.3f}")
        print("Ranks:", pivot.rank(axis=1).mean().round(2).sort_values())


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
                        'group': record.get('group'),
                        'width': record.get('width'),
                        'height': record.get('height'),
                        'bit_depth': record.get('bit_depth'),
                        'num_aovs': record.get('num_aovs'),
                    }

                    # maybe del
                    row['cores'] = float(row['cores']) if row['cores'] is not None else np.nan

                    for k, v in record.get('scan', {}).items():
                        if isinstance(v, dict):
                            for rk, rv in v.items():
                                row[f'scan.{k}.{rk}'] = rv
                        else:
                            row[f'scan.{k}'] = v

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


def query_stats(df, layout=['scan'], cores='all', groups='all', metrics=['read_ms', 'write_ms', 'size_kb'], exclude_methods=[], aggregate=True):
    df_filtered = df.copy()

    if exclude_methods:
        df_filtered = df_filtered[~df_filtered['method'].isin(exclude_methods)]

    if cores != 'all':
        df_filtered = df_filtered[df_filtered['cores'].isin(cores if isinstance(cores, list) else [cores])]

    if groups != 'all':
        df_filtered = df_filtered[df_filtered['group'].isin(groups if isinstance(groups, list) else [groups])]

    cols_to_select = []
    for l in layout:
        cols_to_select.extend([f'{l}.{m}' for m in metrics if f'{l}.{m}' in df_filtered.columns])

    if not cols_to_select:
        print(f"No columns for {layout}.{metrics}")
        return pd.DataFrame()

    if aggregate:
        df_filtered['layout'] = layout[0] if len(layout) == 1 else 'mixed'

        group_cols = ['cores', 'method', 'layout']
        agg_cols = [col for col in cols_to_select if col in df_filtered.columns]
        return df_filtered.groupby(group_cols)[agg_cols].mean().round(2).reset_index()
    else:
        df_filtered['layout'] = layout[0] if len(layout) == 1 else 'mixed'
        raw_cols = ['file', 'cores', 'method', 'layout'] + cols_to_select
        return df_filtered[raw_cols].copy()

def lighten_color(color, factor=0.7):
    color = plt.cm.colors.to_rgb(color)
    return tuple(c + (1-c)*factor for c in color)

def plot_bar_chart(df, stat_col, title='', save=False, filename=''):
    scan_col = f'scan.{stat_col}'
    tiled_col = f'tiled.{stat_col}'

    # Filter to available methods, enforce order
    available_methods = [m for m in COMPRESSION_METHODS if m in df['method'].values]
    df_plot = df[df['method'].isin(available_methods)].copy()
    df_plot['method'] = pd.Categorical(df_plot['method'], categories=available_methods, ordered=True)
    df_plot = df_plot.sort_values('method').reset_index(drop=True)

    has_cores = 'cores' in df_plot.columns and len(df_plot['cores'].unique()) > 1
    has_tiled = tiled_col in df_plot.columns

    fig, ax = plt.subplots(figsize=(14, 7))
    all_bars = []
    graph_title = title or f'{stat_col.title().replace(".", " vs ")}'

    if has_cores and not has_tiled:
        pivot_data = (df_plot.groupby(['method', 'cores'], observed=True)[scan_col]
                      .mean().unstack(fill_value=np.nan))

        cores_list = sorted(pivot_data.columns.astype(float))[:2]
        x = np.arange(len(pivot_data))
        width = 0.35

        method_colors = [METHOD_COLOR_MAP.get(m, '#888') for m in pivot_data.index]

        for i, cores_val in enumerate(cores_list):
            heights = pivot_data[cores_val].fillna(0).values
            offset = x + (i - 0.5) * width

            # 1c: full color, 16c: lighter
            bar_colors = method_colors if i == 0 else [lighten_color(c, 0.6) for c in method_colors]
            label = f'{int(cores_val)}c'
            bars = ax.bar(offset, heights, width, label=label, alpha=0.9,
                          color=bar_colors, edgecolor='black', linewidth=1.2)
            all_bars.extend(bars)

        ax.set_xticks(x)
        xticklabels = [m.replace('_COMPRESSION', '').split('_')[-1] for m in pivot_data.index]
        ax.set_xticklabels(xticklabels, rotation=45, ha='right')



    elif has_tiled:

        scan_means = df_plot.groupby('method', observed=True)[scan_col].mean()
        tiled_means = df_plot.groupby('method', observed=True)[tiled_col].mean()
        methods = scan_means.index.tolist()

        x = range(len(methods))
        width = 0.35

        method_colors = [METHOD_COLOR_MAP.get(m, '#888') for m in methods]
        scan_colors = method_colors  # Full color
        tiled_colors = [lighten_color(c, 0.6) for c in method_colors]  # 40% lighter

        bars1 = ax.bar([i - width / 2 for i in x], scan_means.values,
                       width, label='Scanline', alpha=0.9,
                       color=scan_colors, edgecolor='black', linewidth=1.2)
        bars2 = ax.bar([i + width / 2 for i in x], tiled_means.values,
                       width, label='Tiled', alpha=0.9,
                       color=tiled_colors, edgecolor='black', linewidth=1.2)

        all_bars = list(bars1) + list(bars2)
        ax.set_xticks(x)
        xticklabels = [m.replace('_COMPRESSION', '').split('_')[-1] for m in methods]
        ax.set_xticklabels(xticklabels, rotation=45, ha='right')

    else:
        means = df_plot.groupby('method')[scan_col].mean()
        x = range(len(means))
        bars = ax.bar(x, means.values, alpha=0.8, width=0.8,
                      color=[METHOD_COLOR_MAP.get(m, '#888') for m in means.index],
                      edgecolor='black', linewidth=1.5)
        all_bars = list(bars)
        xticklabels = [m.replace('_COMPRESSION', '').split('_')[-1] for m in means.index]
        ax.set_xticklabels(xticklabels, rotation=45, ha='right')

    ax.set_ylabel(f'{stat_col.replace(".", " (")}{" ms"}', fontweight='bold', fontsize=12)
    ax.set_title(graph_title, fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, axis='y', alpha=0.3, linestyle='-', zorder=0)
    if all_bars:
        ax.legend(loc='upper right', framealpha=0.95, fontsize=11)

    plt.tight_layout()
    if save:
        os.makedirs(graphs_dir, exist_ok=True)
        fpath = os.path.join(graphs_dir, filename)
        plt.savefig(fpath, dpi=300, bbox_inches='tight', facecolor='white')
        print(f'Saved: {fpath} | Methods: {len(available_methods)}')
    plt.show()

def plot_compression_scatter_avg(df, x_col, y_col, layout='scan', cores=[1], categories=[],
                                title='', exclude_methods=None, save=False, filename=None):
    df = df.copy()

    if not isinstance(cores, list): cores = [cores]
    if exclude_methods: df = df[~df['method'].isin(exclude_methods)]

    size_col = f'{layout}.size_kb'

    df['cores_clean'] = pd.to_numeric(df['cores'], errors='coerce')
    df_filtered = df[df['cores_clean'].notna() & df['cores_clean'].isin([int(c) for c in cores])].copy()
    df_filtered = df_filtered.drop(columns=['cores_clean'])

    needed = [x_col, y_col]

    avg_df = df_filtered.groupby(['category', 'method'])[needed].mean().reset_index()
    fig, axes = plt.subplots(len(categories), 1, figsize=(10, 18), sharex=True)
    fig.suptitle(title, fontsize=16, y=0.99)

    all_handles = []
    all_labels = []

    for i, cat in enumerate(categories):
        ax = axes[i]
        df_cat = avg_df[avg_df['category'] == cat].copy()

        if len(df_cat) == 0:
            ax.text(1 , 0.5, f'No {cat} data', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'{cat}')
            continue

        for method in df_cat['method'].unique():
            df_m = df_cat[df_cat['method'] == method]
            x_val, y_val, size_val = df_m[[x_col, y_col, size_col]].iloc[0]

            handle = ax.scatter(x_val, y_val, s=200,
                       color=METHOD_COLOR_MAP.get(method, '#888'),
                       alpha=0.85, edgecolors='black', linewidth=1.5, zorder=5)

            short_name = method.replace('_COMPRESSION', '').split('_')[-1]

            texts = [ax.annotate(short_name, (x_val, y_val),
                        xytext=(6, 6), textcoords='offset points',
                        fontsize=10, fontweight='bold')]

            all_handles.append(handle)
            all_labels.append(short_name)

        ax.grid(True, alpha=0.3, zorder=0)
        n_methods = len(df_cat)
        ax.set_title(f'{cat} ({n_methods} methods)')
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)

    seen = set()
    unique_handles = []
    unique_labels = []
    for label, handle in zip(all_labels, all_handles):
        if label not in seen:
            seen.add(label)
            unique_labels.append(label)
            unique_handles.append(handle)

    fig.legend(unique_handles, unique_labels,
               loc='upper right', bbox_to_anchor=(0.98, 0.98), fontsize=9,
               title='Methods', title_fontsize=10, framealpha=0.95)

    plt.tight_layout()
    plt.subplots_adjust(right=0.85)  # Reserve space for legend

    if save and filename:
        fpath = os.path.join(graphs_dir, filename)
        plt.savefig(fpath, dpi=300, bbox_inches='tight')

    plt.show()



def roi_full_table(df):
    scan_roi = sorted([c for c in df if 'scan.roi_decode_ms.ROI_' in c])
    tile_roi = sorted([c for c in df if 'tiled.roi_decode_ms.ROI_' in c])

    print(f"📊 {len(scan_roi)} ROIs × 12 codecs")
    roi_means = df[['method'] + scan_roi + tile_roi].groupby('method').mean()

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(roi_means.round(1))
    pd.reset_option('display.max_columns')



def analyse(dir_path):
    plt.style.use('seaborn-v0_8-paper')

    df = load_data(dir_path)
    print(f"Loaded: {len(df)} rows, {len(df['file'].unique())} images")
    print(f"Cores: {sorted(df['cores'].unique())}")
    groups = sorted([g for g in df['group'].dropna().unique() if g is not None])
    print(f"Groups: {groups}")

    exclude_lossy = ['NO_COMPRESSION', 'RLE_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION', "PXR24_COMPRESSION", "DWAA_COMPRESSION", "DWAB_COMPRESSION"]
    exclude_lossy_extremes = ['B44_COMPRESSION', 'B44A_COMPRESSION']

    cats = ['Geo', 'Particles', 'VDB', 'Netflix']



    df['category'] = df['group'].map(GROUP_CATEGORIES)
    cats = ['Geo', 'Particles', 'VDB', 'Netflix']

    # 1-core aggregation
    df_agg_1c = df[df['cores'] == 1].groupby(['category', 'method'])[
        ['scan.read_ms', 'scan.size_kb']].mean().reset_index()
    df_agg_1c['cores'] = 1


    df_agg = df.groupby(['category', 'method'])[['scan.read_ms', 'scan.size_kb']].mean().reset_index()


    # Image differences
    # plot_compression_scatter_avg(df_agg_1c, 'scan.read_ms', 'scan.size_kb', cores=[1],
    #                              categories=cats,
    #                              title=f'AVG Encode vs Decode by Image Type (1 core)',
    #                              filename='avg_scan_encode_vs_decode_1c.png',
    #                              save=True)
    #


    # df_agg_16c = df[df['cores'] == 16].groupby(['category', 'method'])[
    #     ['scan.read_ms', 'scan.size_kb']].mean().reset_index()
    # df_agg_16c['cores'] = 16
    #
    # plot_compression_scatter_avg(df_agg_16c, 'scan.read_ms', 'scan.size_kb', cores=[16],
    #                              categories=cats,
    #                              title=f'AVG Encode vs Decode by Image Type (16 cores)',
    #                              filename='avg_scan_encode_vs_decode_16c.png',
    #                              save=True)




    # methods 1 vs 16 cores
    # df_read = query_stats(df, layout=['scan'], cores=[1, 16], aggregate=False)  # Raw 648+ rows
    # plot_bar_chart(df_read, 'read_ms', 'Scanline 1 vs 16-Core Read', save=True, filename='scan_read_1-16c.png')
    # plot_bar_chart(df_read, 'write_ms', 'Scanline 1 vs 16-Core Write', save=True, filename='scan_write_1-16c.png')
    # plot_bar_chart(df_read, 'size_kb', 'Scanline 1 vs 16-Core Size', save=True, filename='scan_size_1-16c.png')



    # df_read = query_stats(df, layout=['scan'], cores=[1, 16])
    # friedman_analysis(df, ['scan.read_ms'], cores=1)
    # friedman_analysis(df, ['scan.write_ms'], cores=1)
    # friedman_analysis(df, ['scan.size_kb'], cores=1)
    #
    # friedman_analysis(df, ['scan.read_ms'], cores=16)
    # friedman_analysis(df, ['scan.write_ms'], cores=16)
    # friedman_analysis(df, ['scan.size_kb'], cores=16)



    # scan - tile
    # df_read = query_stats(df, layout=['scan', 'tiled'], cores=[1, 16])

    # friedman_analysis(df, ['scan.read_ms'], cores=1)
    # friedman_analysis(df, ['scan.write_ms'], cores=1)
    # friedman_analysis(df, ['scan.size_kb'], cores=1)
    #
    # friedman_analysis(df, ['scan.read_ms'], cores=16)
    # friedman_analysis(df, ['scan.write_ms'], cores=16)
    # friedman_analysis(df, ['scan.size_kb'], cores=16)
    #
    # friedman_analysis(df, ['tiled.read_ms'], cores=1)
    # friedman_analysis(df, ['tiled.write_ms'], cores=1)
    # friedman_analysis(df, ['tiled.size_kb'], cores=1)
    #
    # friedman_analysis(df, ['tiled.read_ms'], cores=16)
    # friedman_analysis(df, ['tiled.write_ms'], cores=16)
    # friedman_analysis(df, ['tiled.size_kb'], cores=16)


    # sumarry
    # summary = df.groupby(['method', 'cores', 'category'])[['scan.read_ms', 'scan.write_ms', 'scan.size_kb']].mean().round(2)
    # summary = summary.reset_index().sort_values(['scan.size_kb', 'method'])






    category = 'Netflix'  # or any group from your list
    df_single_cat = df[df['category'] == category].copy()
    #

    # Scan vs Tiled, all cores averaged
    # df_all = query_stats(df, layout=['scan', 'tiled'], cores='all', aggregate=False)
    # plot_bar_chart(df_all, 'read_ms', 'Scanline vs Tiled Read Speed (All Cores Avg)',
    #                save=True, filename='scan_tiled_read.png')
    # plot_bar_chart(df_all, 'write_ms', 'Scanline vs Tiled Write Speed (All Cores Avg)',
    #                save=True, filename='scan_tiled_write.png')
    # plot_bar_chart(df_all, 'size_kb', 'Scanline vs Tiled File Size (All Cores Avg)',
    #                save=True, filename='scan_tiled_size.png')


    rois = ['roi_decode_ms.ROI_10%-40%', 'roi_decode_ms.ROI_45%-55%', 'roi_decode_ms.ROI_25%-75%']
    roi_metrics = rois.copy()
    roi_metrics = ['read_ms', 'write_ms', 'size_kb',
                                      'roi_decode_ms.ROI_10%-40%', 'roi_decode_ms.ROI_45%-55%', 'roi_decode_ms.ROI_25%-75%']


    df_all = query_stats(df, layout=['scan', 'tiled'], cores='all',
                         metrics=roi_metrics, aggregate=False)



    #all cores roi
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_10%-40%', 'ROI 10-40%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_10-40.png', save=True)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_45%-55%', 'ROI 45-55%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_45-55.png', save=True)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_25%-75%', 'ROI 25-75%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_25-75.png', save=True)



    df_all = query_stats(df, layout=['scan', 'tiled'], cores=[1],
                         metrics=roi_metrics, aggregate=False)

    rois = ['roi_decode_ms.ROI_10%-40%', 'roi_decode_ms.ROI_45%-55%', 'roi_decode_ms.ROI_25%-75%']

    for core in [1, 16]:
        for roi in rois:
            friedman_analysis(df, [roi], cores=[core])

    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_10%-40%', 'ROI 10-40%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_10-40_1c.png', save=True)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_45%-55%', 'ROI 45-55%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_45-55_1c.png', save=True)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_25%-75%', 'ROI 25-75%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_25-75_1c.png', save=True)

    df_all = query_stats(df, layout=['scan', 'tiled'], cores=[16],
                         metrics=roi_metrics, aggregate=False)
    friedman_analysis(df, ['scan.read_ms'], cores=1)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_10%-40%', 'ROI 10-40%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_10-40_16c.png', save=True)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_45%-55%', 'ROI 45-55%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_45-55_16c.png', save=True)
    # plot_bar_chart(df_all, 'roi_decode_ms.ROI_25%-75%', 'ROI 25-75%: Scan vs Tiled',
    #                filename='scan_tiled_ROI_25-77_16c.png', save=True)

    return



def plot_nuke_fps_bars(df_fps, title='', save=False, filename=''):
    df_fps['order'] = df_fps['compression'].map({m: i for i, m in enumerate(COMPRESSION_METHODS)})
    df_fps = df_fps.sort_values('order').reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(df_fps))
    width = 0.8

    means = df_fps.groupby('compression', sort=False).mean().reset_index()
    x = np.arange(len(means))
    width = 0.8

    bars = ax.bar(x, means['overall_avg_fps'], width,
                  yerr=means['overall_std_fps'], capsize=5,
                  alpha=0.9, edgecolor='black', linewidth=1.2,
                  color=[METHOD_COLOR_MAP.get(m, '#888') for m in means['compression']])

    ax.set_ylabel('Avg FPS', fontweight='bold', fontsize=12)
    ax.set_title(title or 'Nuke Read Performance by Compression',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    xticklabels = [m.replace('_COMPRESSION', '').split('_')[-1] for m in df_fps['compression']]
    ax.set_xticklabels(xticklabels, rotation=45, ha='right')
    ax.grid(True, axis='y', alpha=0.3, linestyle='-', zorder=0)

    for i, (bar, fps, std) in enumerate(zip(bars, df_fps['overall_avg_fps'], df_fps['overall_std_fps'])):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height + std * 0.1,
                f'{fps:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    plt.tight_layout()
    if save:
        os.makedirs(graphs_dir, exist_ok=True)
        fpath = os.path.join(graphs_dir, filename)
        plt.savefig(fpath, dpi=300, bbox_inches='tight', facecolor='white')
        print(f'Saved: {fpath}')
    plt.show()


def load_nuke_results(nuke_json_path):
    with open(nuke_json_path, 'r') as f:
        nuke_data = json.load(f)

    fps_data = []
    for record in nuke_data:
        fps_data.append({
            'compression': record['compression'],
            'overall_avg_fps': record['overall_avg_fps'],
            'overall_std_fps': record['overall_std_fps']
        })
    return pd.DataFrame(fps_data)



df_nuke = load_nuke_results(r"C:\Users\matsv\Desktop\gw\scripts\results\nuke_benchmark_complete_20260116-030856.json")
plot_nuke_fps_bars(df_nuke, title='Nuke FPS: 10 passes × 9 sequences', save=True, filename='nuke_fps.png')

analyse(result_dir)
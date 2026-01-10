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


def friedman_analysis(df, metrics, cores=1, exclude_methods=None):

    if exclude_methods:
        df = df[~df['method'].isin(exclude_methods)]

    subset = df[df['cores'] == cores].copy()

    print(f"\n{'=' * 60}")
    print(f"Friedman Analysis (cores={cores}, n={subset['file'].nunique()} images)")
    print(f"{'=' * 60}")
    print(f"Files/method: {subset.groupby('method')['file'].nunique().to_dict()}")

    for metric in metrics:
        if metric not in subset.columns:
            print(f"{metric} not found")
            continue

        # Pivot: rows=files, cols=methods, values=metric
        pivot = subset.pivot_table(
            index='file',
            columns='method',
            values=metric
        ).dropna()

        if pivot.shape[0] < 2 or pivot.shape[1] < 3:
            print(f"{metric}: Insufficient data (n={pivot.shape[0]}, methods={pivot.shape[1]})")
            continue

        # Friedman test
        stat, p = friedmanchisquare(*[pivot[col] for col in pivot.columns])
        ranks = pivot.rank(axis=1).mean().sort_values()

        print(f"\n{metric}:")
        print(f"  χ²={stat:.2f}, p={p:.2e} (n={pivot.shape[0]} images)")
        print(f"  Ranks (lower=best):")
        for method, rank in ranks.items():
            print(f"    {method:30s}: {rank:5.2f}")

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


def query_stats(df, layout='scan', cores='all', groups='all', metrics=['read_ms', 'write_ms', 'size_kb'], exclude_methods=[]):
    df_filtered = df.copy()

    if exclude_methods:
        df_filtered = df_filtered[~df['method'].isin(exclude_methods)]

    # cores
    if cores != 'all':
        df_filtered = df_filtered[df_filtered['cores'].isin(cores if isinstance(cores, list) else [cores])]

    # groups
    if groups != 'all':
        df_filtered = df_filtered[df_filtered['group'].isin(groups if isinstance(groups, list) else [groups])]

    # cols
    cols_to_agg = [f'{layout}.{m}' for m in metrics if f'{layout}.{m}' in df_filtered.columns]

    if not cols_to_agg:
        print(f"No columns for {layout}.{metrics}")
        return pd.DataFrame()

    return df_filtered.groupby(['cores', 'method'])[cols_to_agg].mean().round(2).reset_index()

def plot_bar_chart(df, stat_col, title_add='', save=False, filename=None):

    if stat_col not in df.columns:
        print(f"Column '{stat_col}' missing")
        return

    # Check if df has 'cores' column (multi-core data)
    has_cores = 'cores' in df.columns and df['cores'].nunique() > 1

    fig, ax = plt.subplots(figsize=(12, 6))
    graph_title = ''

    if has_cores:
        # MULTI-CORE: Pivot & group bars
        pivot_data = df.pivot(index='method', columns='cores', values=stat_col)
        cores_to_plot = sorted(pivot_data.columns.tolist())[:2]  # Max 2 core counts

        x = range(len(pivot_data))
        width = 0.35

        # Bar 1 (first core count)
        bars1 = ax.bar([i - width / 2 for i in x], pivot_data[cores_to_plot[0]],
                       width, label=f'{cores_to_plot[0]}-Core', alpha=0.8,
                       color=[METHOD_COLOR_MAP.get(m, 'gray') for m in pivot_data.index],
                       edgecolor = 'black', linewidth = 1)

        # Bar 2 (second core count, if exists)
        if len(cores_to_plot) > 1:
            bars2 = ax.bar([i + width / 2 for i in x], pivot_data[cores_to_plot[1]],
                           width, label=f'{cores_to_plot[1]}-Core', alpha=0.8,
                           color=[METHOD_COLOR_MAP.get(m, 'gray') for m in pivot_data.index],
                           edgecolor='black', linewidth=1)
            all_bars = list(bars1) + list(bars2)
        else:
            all_bars = list(bars1)

        # Labels
        graph_title = f"{cores_to_plot[0]} vs {cores_to_plot[1]} cores {stat_col} ({title_add})"
        ax.set_xticks(x)
        ax.set_xticklabels([m.split('_')[0] for m in pivot_data.index], rotation=45, ha='right')

    else:
        # SINGLE-CORE: Simple bars
        methods = df['method'].values
        values = df[stat_col].values

        num_cores = df.pivot(index='method', columns='cores', values=stat_col)
        method = df.pivot(index='method', columns='cores', values=stat_col)

        bar_colors = [METHOD_COLOR_MAP.get(m, 'gray') for m in methods]
        all_bars = ax.bar(range(len(methods)), values, color=bar_colors, alpha=0.8,
                          edgecolor='black', linewidth=1.5)

        ax.set_xticks(range(len(methods)))
        ax.set_xticklabels([m.split('_')[0] for m in methods], rotation=45, ha='right')

        if num_cores != 1:
            graph_title = f"{num_cores} core {stat_col} ({title_add})"
        else:
            graph_title = f"{num_cores} cores {stat_col} ({title_add})"

    # Common labels
    ax.set_ylabel(stat_col, fontweight='bold')

    ax.set_title(graph_title, fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    # ax.legend()

    # Value labels on bars
    for bar in all_bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    if save:
        fname = filename or f'{stat_col.replace(".", "_")}.png'
        fpath = os.path.join(graphs_dir, fname)
        plt.savefig(fpath, dpi=300)
        print(f'Saved: {fpath}')

    plt.show()


def plot_compression_scatter_avg(df, x_col, y_col, layout='scan', cores=[1], exclude_methods=None, save=False,
                                 filename=None):
    df = df.copy()

    if not isinstance(cores, list): cores = [cores]
    if exclude_methods: df = df[~df['method'].isin(exclude_methods)]

    size_col = f'{layout}.size_kb'

    df_filtered = df[df['cores'].astype(int).isin([int(c) for c in cores])].copy()

    needed = [x_col, y_col, size_col]
    missing = [c for c in needed if c not in df_filtered.columns]
    if missing:
        print(f"Missing columns: {missing}")
        print(f"Available: {list(df_filtered.columns)}")
        return

    avg_df = df_filtered.groupby(['category', 'method'])[needed].mean().reset_index()

    categories = ['Netflix', 'Geo', 'Particles', 'VDB', 'Other']

    fig, axes = plt.subplots(5, 1, figsize=(14, 20), sharex=True)
    fig.suptitle(f'{layout.upper()} AVG Encode vs Decode (bubble=File Size, {cores[0]}C)', fontsize=16)

    for i, cat in enumerate(categories):
        ax = axes[i]
        df_cat = avg_df[avg_df['category'] == cat].copy()

        if len(df_cat) == 0:
            ax.text(0.5, 0.5, f'No {cat} data', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(f'{cat}')
            continue

        for method in df_cat['method'].unique():
            df_m = df_cat[df_cat['method'] == method]
            x_val, y_val, size_val = df_m[[x_col, y_col, size_col]].iloc[0]

            # Scale bubble size
            bubble_size = max(40, min(600, size_val * 0.8))

            ax.scatter(x_val, y_val, s=bubble_size,
                       color=METHOD_COLOR_MAP.get(method, '#888'),
                       alpha=0.85, edgecolors='black', linewidth=1.5, zorder=5)

            # Clean label
            short_name = method.replace('_COMPRESSION', '').split('_')[-1]
            ax.annotate(short_name, (x_val, y_val),
                        xytext=(6, 6), textcoords='offset points',
                        fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.9))

        ax.grid(True, alpha=0.3, zorder=0)
        n_methods = len(df_cat)
        ax.set_title(f'{cat} ({n_methods} methods)')
        if i == 4:
            ax.set_xlabel('Encode time (ms)')
            ax.set_ylabel('Decode time (ms)')
        else:
            ax.set_ylabel('Decode (ms)')

    legend_methods = ['PIZ', 'ZIP', 'ZIPS', 'HTJ2K256', 'HTJ2K32']
    legend_colors = [METHOD_COLOR_MAP.get(f'{m}_COMPRESSION', '#888') for m in legend_methods]
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='o', color='w',
                              markerfacecolor=c, markersize=20,
                              markeredgecolor='black') for c in legend_colors]
    fig.legend(legend_elements, legend_methods, loc='upper right', bbox_to_anchor=(0.98, 0.98))

    plt.tight_layout()
    plt.subplots_adjust(right=0.82)

    if save and filename:
        fpath = os.path.join(graphs_dir, filename)
        plt.savefig(fpath, dpi=300, bbox_inches='tight')
        print(f'✅ Saved: {fpath} | {len(avg_df)} total method-category pairs')

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

GROUP_CATEGORIES = {
    'Chimera': 'Netflix',
    'CosmosLaundromat': 'Netflix',
    'Meridian': 'Netflix',
    'Sparks': 'Netflix',

    '0010_TestSand_Robot_Comp': 'Geo',
    '0160_Shadow_Comp': 'Geo',
    '0130_Geo_Comp': 'Geo',
    '0160_Geo_Front_Comp': 'Geo',
    '0160_Geo_Back_Comp': 'Geo',


    '0010_TestSand_Sand_Comp': 'Particles',
    '0130_Wind_Comp': 'Other',

    '0010_TestSand_VDB_Comp': 'Other',
    '0130_VDB_Comp': 'VDB'
}

def analyse(dir_path):
    plt.style.use('seaborn-v0_8-paper')

    df = load_data(dir_path)
    print(f"Loaded: {len(df)} rows, {len(df['file'].unique())} images")
    print(f"Cores: {sorted(df['cores'].unique())}")
    print(f"Groups: {sorted(df['group'].unique())}")

    exclude_lossy = ['NO_COMPRESSION', 'RLE_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION', "PXR24_COMPRESSION", "DWAA_COMPRESSION", "DWAB_COMPRESSION"]
    exclude_lossy_extremes = ['NO_COMPRESSION', 'RLE_COMPRESSION', 'B44_COMPRESSION', 'B44A_COMPRESSION']

    # 1. Single-core, all groups, read speed (SCAN)
    print("\n\n[1] SCANLINE - 1-CORE READ SPEED")

    df_1c_read = query_stats(df, layout='scan', cores=[1, 16], exclude_methods=exclude_lossy)
    # plot_bar_chart(df_1c_read, 'scan.read_ms', 'Scanline 1 vs 16-Core Read Speed', save=False, filename='1_scan_read_1c.png')
    # plot_bar_chart(df_1c_read, 'scan.size_kb', 'Scanline 1-Core Read Speed', save=False, filename='1_scan_read_1c.png')
    # friedman_analysis(df, ['scan.read_ms'], cores=1)

    df['category'] = df['group'].map(GROUP_CATEGORIES)

    # for category in df['category'].unique():
    #     df_category = df[df['category'] == category]
    #     groups_in_cat = df_category['group'].unique()
    #     df_1c_read = query_stats(df_category, layout='scan', cores=[1, 16],
    #                              metrics=['read_ms'], exclude_methods=exclude_lossy)
    #     plot_bar_chart(df_1c_read, 'scan.read_ms', f'{category}', save=False, filename='1_scan_read_1c.png')


    # TILED version (HTJ2K shines)
    plot_compression_scatter_avg(df, 'scan.write_ms', 'scan.read_ms', cores=[1],
                                 exclude_methods=exclude_lossy_extremes, filename='avg_scan_encode_vs_decode.png')

    # plot_compression_scatter_avg(df, 'tiled.write_ms', 'tiled.read_ms', cores=[16],
    #                              exclude_methods=exclude_lossy_extremes, filename='avg_tiled_encode_vs_decode.png')







    return

    # 2. 16-core, all groups, compression ratio
    print("\n\n[2] SCANLINE - 16-CORE SIZE")
    df_16c_size = query_stats(df, layout='scan', cores=[16], metrics=['size_kb'])
    plot_bar_chart(df_16c_size, 'scan.size_kb', 'Scanline 16-Core File Size', save=False, filename='2_scan_size_16c.png')

    # 3. Tiled, 16-core, read (HTJ2K should shine here)
    print("\n\n[3] TILED - 16-CORE READ SPEED")
    df_tiled_read = query_stats(df, layout='tiled', cores=[16], metrics=['read_ms'], exclude_methods=exclude_lossy)
    plot_bar_chart(df_tiled_read, 'tiled.read_ms', 'Tiled 16-Core Read Speed (HTJ2K Advantage)', save=True,
              filename='3_tiled_read_16c.png')
    friedman_analysis(df, ['tiled.read_ms'], cores=16)

    # 4. Per-group analysis (Chimera only)
    print("\n\n[4] CHIMERA GROUP - SCAN vs TILED")
    df_chimera = df[df['group'] == 'Chimera']
    df_c_scan = df_chimera[df_chimera['cores'] == 1].groupby('method')['scan.read_ms'].mean().reset_index()
    df_c_scan.columns = ['method', 'scan.read_ms']
    plot_bar_chart(df_c_scan, 'scan.read_ms', 'Chimera 1-Core Scan Read', save=True, filename='4_chimera_scan_1c.png')

    # 5. ROI speedup comparison
    print("\n\n[5] ROI DECODE COMPARISON")
    roi_cols_scan = [c for c in df.columns if 'scan.roi_decode_ms.ROI_' in c]
    roi_cols_tiled = [c for c in df.columns if 'tiled.roi_decode_ms.ROI_' in c]

    if roi_cols_scan and roi_cols_tiled:
        print(f"ROI columns (scan): {len(roi_cols_scan)}")
        print(f"ROI columns (tiled): {len(roi_cols_tiled)}")

        # ROI speedup: scan/tiled (lower = tiled wins)
        roi_speedup = {}
        for s_col, t_col in zip(roi_cols_scan, roi_cols_tiled):
            roi_name = s_col.split('ROI_')[-1]
            s_mean = df[s_col].mean()
            t_mean = df[t_col].mean()
            if t_mean > 0:
                roi_speedup[roi_name] = s_mean / t_mean

        print("\n⚡ ROI Speedup (Scan / Tiled, >1 = Tiled Wins):")
        for roi, speedup in sorted(roi_speedup.items()):
            print(f"  {roi:15s}: {speedup:.2f}x")


analyse(result_dir)
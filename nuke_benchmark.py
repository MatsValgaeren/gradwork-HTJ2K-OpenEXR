import os
import nuke
import time
import tempfile
import statistics
import re
import shutil
import json
import datetime

input_dir = r'E:\gw\test'
temp_dir = r'E:\gw\temp'
result_dir = r'.\..\results'

compression_map = {
    'NO_COMPRESSION': 'none',
    'RLE_COMPRESSION': 'rle',
    'ZIP_COMPRESSION': 'zip',
    'PIZ_COMPRESSION': 'piz',
    'ZIPS_COMPRESSION': 'zips',
    'PXR24_COMPRESSION': 'pxr24',
    'B44_COMPRESSION': 'b44',
    'B44A_COMPRESSION': 'b44a',
    'DWAA_COMPRESSION': 'dwaa',
    'DWAB_COMPRESSION': 'dwab',
    'HTJ2K32_COMPRESSION': 'htj2k',
    'HTJ2K256_COMPRESSION': 'htj2k'
}


def recompress_nuke(input_path, output_path, comp_name):
    read_node = nuke.createNode('Read')
    read_node['file'].setValue(input_path.replace('\\', '/'))
    read_node['reload'].execute()

    reformat_node = nuke.createNode('Reformat')
    reformat_node.setInput(0, read_node)
    reformat_node['format'].setValue('HD_1080')

    write_node = nuke.createNode('Write')
    write_node.setInput(0, reformat_node)
    write_node['file'].setValue(output_path.replace('\\', '/'))
    write_node['file_type'].setValue('exr')
    write_node['datatype'].setValue('32 bit float')
    write_node['compression'].setValue(comp_name)


    first_frame = int(input_path[-11:-7])
    last_frame = first_frame + 9

    nuke.execute(write_node, first_frame, last_frame, 1)

    nuke.delete(read_node)
    nuke.delete(reformat_node)
    nuke.delete(write_node)
    return True

def remove_files(dir):
    for root, dirs, files in os.walk(dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            os.remove(file_path)


def create_read_nodes(compression_name):
    oiio_comp = compression_map[compression_name]
    comp_short = compression_name.split("_")[0]  # 'NO', 'HTJ2K256'

    for item in os.listdir(input_dir):

        input_folder = os.path.join(input_dir, item)
        no_files = [f for f in os.listdir(input_folder) if f.endswith('_NO.exr')]
        if not no_files:
            continue
        input_file = os.path.join(input_folder, no_files[0])

        base_name = os.path.basename(input_file)[:-7]

        output_folder = os.path.join(temp_dir, item)
        os.makedirs(output_folder, exist_ok=True)

        output_file = f"{base_name}_{comp_short}.%04d.exr"
        new_file_path = os.path.join(output_folder, output_file)

        recompress_nuke(input_file, new_file_path, oiio_comp)


def delete_folder_contents(folder_path):
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
        except (PermissionError, OSError) as e:
            print(f"Skip locked: {item_path} ({e})")
            continue

    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                os.unlink(os.path.join(root, file))
    except:
        pass


def nuke_benchmark():
    for node in nuke.allNodes('Read'):
        nuke.delete(node)

    all_results = []
    for comp_name in compression_map:
        print(f"\n=== {comp_name} ===")
        result = nuke_read_benchmark(comp_name)  # Returns JSON
        all_results.append({"compression": comp_name, **result})

    final_file = os.path.join(result_dir,
                              f"nuke_benchmark_complete_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    os.makedirs(result_dir, exist_ok=True)
    with open(final_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nCOMPLETE RESULTS: {final_file}")


def get_base_and_frame(filename):
    clean = filename.rsplit('.', 1)[0]

    if '_' in clean:
        parts = clean.rsplit('_', 1)
        if len(parts) == 2 and not parts[1].isdigit():
            clean = parts[0]

    # Now extract frame (last 4-5 digits)
    match = re.search(r'(\d{4,5})$', clean)
    if match:
        frame_part = match.group(1)
        base_name = clean[:-len(frame_part)]
    else:
        base_name, frame_part = clean, None

    return base_name.strip('_'), frame_part



def nuke_read_benchmark(comp):
    for node in nuke.allNodes('Read'):
        nuke.delete(node)
    print("=== NUKE READ BENCHMARK ===")
    return benchmark_all_temp_dirs(num_passes=10, comp_name=comp)


def benchmark_all_temp_dirs(num_passes=3, comp_name=''):
    all_results = {}
    comp_path = os.path.join(temp_dir, comp_name)
    for folder_name in os.listdir(comp_path):

        folder_path = os.path.join(comp_path, folder_name)
        ext = comp_name.split('_')[0]
        print(folder_path)
        if not os.path.isdir(folder_path):
            continue

        exr_files = [f for f in os.listdir(folder_path) if f.endswith('.exr')]
        prefixes = {}
        for f in exr_files:
            prefix = f[:-8]
            prefixes.setdefault(prefix, []).append(f)

        print('lekkah')
        seq_prefix = folder_name + '_' + ext + '_'

        seq_path = os.path.join(folder_path, folder_name + '_####_' + ext + '.exr').replace('\\', '/')
        print(seq_path)

        # Create ONE Read node
        read_node = nuke.createNode('Read')
        read_node['file'].setValue(seq_path)
        read_node['label'].setValue(folder_name)

        first_exr = exr_files[0]
        match = re.search(r'_(\d{4,})(?=_|$)', first_exr)
        first_frame = int(match.group(1))
        read_node['first'].setValue(first_frame)
        read_node['last'].setValue(first_frame + 9)

        print(f"Benchmarking {folder_name}: {seq_prefix}%04d.exr")

        nuke.selectAll()
        nuke.invertSelection()
        read_node.setSelected(True)

        result_dict = benchmark_selected_reads_stable([read_node], num_passes, ext, first_frame=first_frame)

        if result_dict:
            all_results[folder_name] = list(result_dict.values())[0]

        nuke.delete(read_node)
        time.sleep(0.2)  # Let Nuke release handles

    if all_results:
        all_fps_flat = [fps for res in all_results.values() for fps in res[2]]
        json_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "num_sequences": len(all_results),
            "num_passes": num_passes,
            "overall_avg_fps": round(statistics.mean(all_fps_flat), 2),
            "overall_std_fps": round(statistics.stdev(all_fps_flat), 2) if len(all_fps_flat) > 1 else 0.0,
            "per_sequence": {
                name: {"avg_fps": round(data[0], 2), "std_fps": round(data[1], 2)}
                for name, data in all_results.items()
            }
        }
        return json_data
    return {}


def benchmark_selected_reads_stable(nodes=None, num_passes=3, exr='NO', first_frame=1001):
    if nodes is None:
        nodes = nuke.selectedNodes()
    read_nodes = [n for n in nodes if n.Class() == 'Read']

    all_results = {}

    for node in read_nodes:
        file_path = node.knob('file').value()

        last_frame = first_frame + 9

        label = node.knob('label').value() or node.name()
        print(f"Testing {label} ({first_frame}-{last_frame})")

        fps_list = []
        for pass_num in range(num_passes):
            temp_dir_bench = tempfile.mkdtemp(prefix="nuke_read_bench_")
            temp_path = os.path.join(temp_dir_bench, "bench.%04d.exr").replace("\\", "/")

            write = nuke.createNode("Write", inpanel=False)
            write.setInput(0, node)
            write["file"].setValue(temp_path)
            write["file_type"].setValue("exr")
            write["compression"].setValue("none")

            try:
                t0 = time.time()
                nuke.execute(write, first_frame, last_frame, 1)
                t1 = time.time()
                fps = 10 / (t1 - t0)
                fps_list.append(fps)
            finally:
                nuke.delete(write)
                shutil.rmtree(temp_dir_bench, ignore_errors=True)

            print(f"  Pass {pass_num + 1}: {fps:.2f} FPS")

        avg_fps = statistics.mean(fps_list)
        std_fps = statistics.stdev(fps_list) if len(fps_list) > 1 else 0.0
        all_results[label] = (avg_fps, std_fps, fps_list)
        print(f"  AVG: {avg_fps:.2f} ± {std_fps:.2f} FPS")

    # Per-sequence summary
    print("\nPer-sequence:")
    print("Seq\tAvg FPS\tStd")
    print("-" * 25)
    for name, (avg, std, fps_list) in sorted(all_results.items()):
        print(f"{name[:15]}\t{avg:.2f}\t{std:.2f}")

    return all_results
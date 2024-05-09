import argparse
import math
import os
import re

import pandas as pd
import tabulate

from sparc.curation.tools.definitions import SIZE_NAME


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s}{SIZE_NAME[i]}"


def convert_to_bytes(size_string):
    m = re.match(r'^(\d+)(B|KiB|MiB|GiB|PiB|EiB|ZiB|YiB)$', size_string)
    if not m:
        raise argparse.ArgumentTypeError("'" + size_string + "' is not a valid size. Expected forms like '5MiB', '3KiB', '400B'.")
    start = m.group(1)
    end = m.group(2)
    return int(start) * math.pow(1024, SIZE_NAME.index(end))


def is_same_file(path1, path2):
    """Test if path1 is the same as path2.  If stat() on either fails and the paths
     are non-empty test if the strings are the same."""
    try:
        return os.path.samefile(path1, path2)
    except FileNotFoundError:
        if path1 and path2:
            return path1 == path2

    return False


def get_absolute_path(dataset_dir, filename):
    if os.path.isabs(filename):
        return filename
    if filename.startswith("files"):
        return os.path.join(dataset_dir, filename)
    if os.path.exists(os.path.join(dataset_dir, "files")):
        dataset_dir = os.path.join(dataset_dir, "files")
    if filename.startswith("derivative"):
        return os.path.join(dataset_dir, filename)
    if os.path.exists(os.path.join(dataset_dir, "derivative")):
        dataset_dir = os.path.join(dataset_dir, "derivative")
    return os.path.join(dataset_dir, filename)


def print_as_table(xlsx_file):
    df = pd.read_excel(xlsx_file)

    headers = [table_header(header) for header in df.keys()]
    print(tabulate.tabulate(df, headers=headers, tablefmt='simple'))


def print_errors(errors):
    for i, e in enumerate(errors):
        print(i + 1, e.get_error_message())


def table_header(in_header):
    if in_header == 'timestamp':
        return 'ts'
    elif in_header == 'file type':
        return 'type'
    elif in_header.startswith('Unnamed'):
        return '*'

    return in_header

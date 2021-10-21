import argparse
import math
import os
import re

import pandas as pd
from sparc.curation.tools.definitions import SIZE_NAME


def is_samefile(loc1, loc2):
    if pd.notnull(loc2):
        if os.path.isfile(loc2):
            return os.path.samefile(loc1, loc2)

    return False


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

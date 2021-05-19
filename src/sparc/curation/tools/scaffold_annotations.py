import argparse
import json
import math
import os
import pandas as pd
from pathlib import Path
import re

VERSION = '1.1.0'


SCAFFOLD_DIR_MIME = 'inode/vnd.abi.scaffold+directory'
SCAFFOLD_FILE_MIME = 'inode/vnd.abi.scaffold+file'
SCAFFOLD_THUMBNAIL_MIME = 'inode/vnd.abi.scaffold+thumbnail'
TARGET_MIMES = [SCAFFOLD_DIR_MIME, SCAFFOLD_FILE_MIME, SCAFFOLD_THUMBNAIL_MIME]

SIZE_NAME = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")


class ScaffoldAnnotationError(object):

    def __init__(self, message):
        self._message = message

    def __str__(self):
        return f'Error: {self._message}'


class ScaffoldAnnotation(object):

    def __init__(self, location, dir_name=None, file=None, thumbnail=None):
        self._dir = dir_name
        self._file = file
        self._thumbnail = thumbnail
        self._location = location

    def location(self):
        post_fix = list(filter(None, [self._dir, self._file, self._thumbnail]))
        return os.path.normpath(os.path.join(self._location, post_fix[0]))

    def set_dir(self, dir_name):
        self._dir = dir_name

    def dir(self):
        return self._dir

    def is_dir(self):
        return self._dir is not None

    def set_file(self, file):
        self._file = file

    def file(self):
        return self._file

    def is_file(self):
        return self._file is not None

    def set_thumbnail(self, thumbnail):
        self._thumbnail = thumbnail

    def thumbnail(self):
        return self._thumbnail

    def is_thumbnail(self):
        return self._thumbnail is not None

    def __eq__(self, other):
        return self.location() == other.location()


def something(base_dir, filename, mime):
    value = None
    if mime in TARGET_MIMES:
        value = ScaffoldAnnotation(base_dir)
        if mime == SCAFFOLD_DIR_MIME:
            value.set_dir(filename)
        elif mime == SCAFFOLD_FILE_MIME:
            value.set_file(filename)
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            value.set_thumbnail(filename)

    return value


def scrape_manifest_content(manifest, data_frame):
    base_dir = os.path.dirname(manifest)
    manifest_annotations = []
    for key in data_frame.keys():
        df = data_frame[key]
        if 'additional types' in df:
            full_results = [something(base_dir, x, y) for x, y in zip(df['filename'], df['additional types'])]
            result = list(filter(None, full_results))
            manifest_annotations.extend(result)

    return manifest_annotations


def scrape_manifest_entries(dataset_dir):
    result = list(Path(dataset_dir).rglob("manifest.xlsx"))
    scaffold_annotations = []
    for r in result:
        xl_file = pd.ExcelFile(r)
        dfs = {sheet_name: xl_file.parse(sheet_name)
               for sheet_name in xl_file.sheet_names}
        scaffold_annotations.extend(scrape_manifest_content(r, dfs))

    return scaffold_annotations


def check_scaffold_annotations(scaffold_annotations):
    errors = []
    for scaffold_annotation in scaffold_annotations:
        location = scaffold_annotation.location()
        if scaffold_annotation.is_dir():
            if not os.path.isdir(location):
                errors.append(ScaffoldAnnotationError(f'Directory "{location}" either does not exist or is not a directory.'))
        elif not os.path.isfile(location):
            errors.append(ScaffoldAnnotationError(f'File "{location}" does not exist.'))

    return errors


def search_for_metadata_files(dataset_dir, max_size):
    metadata = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        meta = False
        if os.path.getsize(r) < max_size:
            try:
                with open(r, encoding='utf-8') as f:
                    file_data = f.read()
            except UnicodeDecodeError:
                continue
            except IsADirectoryError:
                continue

            try:
                data = json.loads(file_data)
                if data:
                    if isinstance(data, list):
                        url_present = True
                        for d in data:
                            if 'URL' not in d:
                                url_present = False

                        meta = url_present
            except json.decoder.JSONDecodeError:
                pass

        if meta:
            metadata.append(ScaffoldAnnotation(os.path.dirname(r), file=os.path.split(r)[1]))

    return metadata


def check_scaffold_metadata_annotated(metadata, annotations):
    errors = []
    for md in metadata:
        if md not in annotations:
            errors.append(ScaffoldAnnotationError(f"Found scaffold metadata file that is not annotated '{md.location()}'."))
    return errors


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


def main():
    parser = argparse.ArgumentParser(description='Check scaffold annotations for a SPARC dataset.')
    parser.add_argument("dataset_dir", help='directory to check.')
    parser.add_argument("-m", "--max-size", help="Set the max size for metadata file. Default is 2MiB", default='2MiB', type=convert_to_bytes)

    args = parser.parse_args()
    scaffold_annotations = scrape_manifest_entries(args.dataset_dir)
    errors = check_scaffold_annotations(scaffold_annotations)
    scaffold_metadata = search_for_metadata_files(args.dataset_dir, args.max_size)

    errors.extend(check_scaffold_metadata_annotated(scaffold_metadata, scaffold_annotations))

    for error in errors:
        print(error)


if __name__ == "__main__":
    main()

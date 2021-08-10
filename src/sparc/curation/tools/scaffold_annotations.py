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

    def __init__(self, message, location):
        self._message = message
        self._location = location
    
    def getLocation(self):
        return self._location

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
        if not value.file():
            value = None
    return value


def scrape_manifest_content(data_frame):
    manifest_annotations = []
    df = data_frame
    if 'additional types' in df:
        full_results = [something(df['manifest_dir'],df['filename'], df['additional types']) for index, df in data_frame.iterrows()]
        result = list(filter(None, full_results))
        manifest_annotations.extend(result)
    return manifest_annotations


def read_manifest(dataset_dir):
    result = list(Path(dataset_dir).rglob("manifest.xlsx"))
    manifestDataFrame = pd.DataFrame()
    for r in result:
        xl_file = pd.ExcelFile(r)
        # print(xl_file)
        for sheet_name in xl_file.sheet_names:
            currentDataFrame = xl_file.parse(sheet_name)
            currentDataFrame['sheet_name'] =sheet_name
            currentDataFrame['manifest_dir'] =os.path.dirname(r)
            manifestDataFrame = pd.concat([currentDataFrame,manifestDataFrame])
    # print(manifestDataFrame)
    return manifestDataFrame


def scrape_manifest_entries(dataset_dir):
    scaffold_annotations = []
    dfs = read_manifest(dataset_dir)
    scaffold_annotations.extend(scrape_manifest_content(dfs))
    return scaffold_annotations


def check_scaffold_annotations(scaffold_annotations):
    errors = []
    for scaffold_annotation in scaffold_annotations:
        location = scaffold_annotation.location()
        if scaffold_annotation.is_dir():
            if not os.path.isdir(location):
                errors.append(ScaffoldAnnotationError(f'Directory "{location}" either does not exist or is not a directory.', location))
        elif not os.path.isfile(location):
            errors.append(ScaffoldAnnotationError(f'File "{location}" does not exist.', location))
    return errors


def search_for_metadata_files(dataset_dir, max_size):
    metadata = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        meta = False
        if os.path.getsize(r) < max_size and os.path.isfile(r):
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
            errors.append(ScaffoldAnnotationError(f"Found scaffold metadata file that is not annotated '{md.location()}'.", md.location()))
    return errors

def annotate_scaffold_file(dataset_dir, file_location):
    manifestDataFrame = read_manifest(dataset_dir)
    fileDF = manifestDataFrame[manifestDataFrame["filename"] == os.path.basename(file_location)]
    # If fileDF is empty, means there's no manifest file contain this file. 
    # Check if there's manifest file under same dir. Add file to the manifest.
    # If no manifest file create new manifest file
    # Todo
    print(fileDF)
    
    for index, row in fileDF.iterrows():
        fileLocation = os.path.join(row["manifest_dir"], row['filename'])
        if os.path.samefile(file_location, fileLocation):
            mDF = pd.read_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"),sheet_name=row["sheet_name"])
            mDF['additional types'][mDF["filename"] == row['filename']] = SCAFFOLD_FILE_MIME
            mDF.to_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"), sheet_name=row["sheet_name"], index=False, header=True)

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

    # args = parser.parse_args()
    dataset_dir = r"C:\Users\ywan787\neondata\curationdata"
    max_size = 1000000000
    scaffold_annotations = scrape_manifest_entries(dataset_dir)
    read_manifest(dataset_dir)
    errors = check_scaffold_annotations(scaffold_annotations)
    scaffold_metadata = search_for_metadata_files(dataset_dir, max_size)

    errors.extend(check_scaffold_metadata_annotated(scaffold_metadata, scaffold_annotations))

    for error in errors:
        print(error)
        annotate_scaffold_file(dataset_dir, error.getLocation())


if __name__ == "__main__":
    main()

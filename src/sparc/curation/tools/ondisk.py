import csv
import json
import os
from pathlib import Path

from sparc.curation.tools.base import Singleton


ZINC_GRAPHICS_TYPES = ["points", "lines", "surfaces", "contours", "streamlines"]


def _is_graphics_entry(entry):
    if 'URL' in entry and 'Type' in entry:
        entry_type = entry['Type']
        if entry_type.lower() in ZINC_GRAPHICS_TYPES:
            return True

    return False


def _is_view_entry(entry):
    if 'URL' in entry and 'Type' in entry:
        entry_type = entry['Type']
        if entry_type.lower() == "view":
            return True

    return False


def test_for_metadata(json_data):
    have_viewable_graphics = False
    have_view_reference = False
    if json_data:
        if isinstance(json_data, list):
            for entry in json_data:
                if not have_viewable_graphics and _is_graphics_entry(entry):
                    have_viewable_graphics = True
                if not have_view_reference and _is_view_entry(entry):
                    have_view_reference = True

    return have_view_reference and have_viewable_graphics


def test_for_view(json_data):
    is_view = False
    if json_data:
        if isinstance(json_data, dict):
            expected_keys = ["farPlane", "nearPlane", "upVector", "targetPosition", "eyePosition"]
            missing_key = False
            for expected_key in expected_keys:
                if expected_key not in json_data:
                    missing_key = True

            is_view = not missing_key

    return is_view


def is_context_data_file(json_data):
    if json_data:
        if isinstance(json_data, dict):
            # "version" and "id" are required keys for a context data file.
            if "version" in json_data and "id" in json_data:
                return json_data["id"] == "sparc.science.context_data"

    return False


def is_annotation_csv_file(csv_reader):
    if csv_reader:
        first = True
        for row in csv_reader:
            if first:
                if len(row) == 2 and row[0] == "Term ID" and row[1] == "Group name":
                    first = False
                else:
                    return False
            elif len(row) != 2:
                return False

        return True

    return False


def is_json_of_type(r, max_size, test_func):
    result = False
    if os.path.getsize(r) < max_size and os.path.isfile(r):
        try:
            with open(r, encoding='utf-8') as f:
                file_data = f.read()
        except UnicodeDecodeError:
            return result
        except IsADirectoryError:
            return result

        try:
            data = json.loads(file_data)
            result = test_func(data)
        except json.decoder.JSONDecodeError:
            return result

    return result


def is_csv_of_type(r, max_size, test_func):
    result = False
    if os.path.getsize(r) < max_size and os.path.isfile(r):
        try:
            with open(r, encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                result = test_func(csv_reader)
        except UnicodeDecodeError:
            return result
        except IsADirectoryError:
            return result
        except csv.Error:
            return result

    return result


def get_view_urls(metadata_file):
    view_urls = []
    try:
        with open(metadata_file, encoding='utf-8') as f:
            file_data = f.read()
        json_data = json.loads(file_data)
        if json_data:
            if isinstance(json_data, list):
                for entry in json_data:
                    if 'URL' in entry and 'Type' in entry:
                        entry_type = entry['Type']
                        if entry_type.lower() == "view":
                            view_url = os.path.join(os.path.dirname(metadata_file), entry['URL'])
                            view_urls.append(view_url)

    except json.decoder.JSONDecodeError:
        return view_urls

    return view_urls


def search_for_metadata_files(dataset_dir, max_size):
    metadata = []
    metadata_views = {}
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        meta = is_json_of_type(r, max_size, test_for_metadata)

        if meta:
            metadata.append(str(r))
            view_urls = get_view_urls(str(r))
            metadata_views[str(r)] = view_urls

    return metadata, metadata_views


def search_for_thumbnail_files(dataset_dir):
    result = list(Path(dataset_dir).rglob("*thumbnail*"))
    list(Path(dataset_dir).rglob("*.png"))
    list(Path(dataset_dir).rglob("*.jpeg"))
    list(Path(dataset_dir).rglob("*.jpg"))
    # For each result:
    #   - Is this file actually an image?
    # Probably just leave this for now and go with the simple name comparison.
    return [str(x) for x in result]


def search_for_view_files(dataset_dir, max_size):
    metadata = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        meta = is_json_of_type(r, max_size, test_for_view)

        if meta:
            metadata.append(str(r))

    return metadata


class OnDiskFiles(metaclass=Singleton):
    # dataFrame_dir = ""
    _onDiskFiles = None
    _scaffold = None

    class Scaffold(object):
        _scaffold_files = {
            'metadata': [],
            'view': [],
            'thumbnail': [],
        }

        _metadata_views = {}

        '''
        _scaffold_structure = {
            'metadata.json':{
                'view.json':'thumbnail.png',
                'view2.json':'thumbnail2.png'
            },
            'metadata2.json':{
                'view.json':'thumbnail.png'
            },
        }

        '''

        def set_metadate_files(self, files, metadata_views):
            self._scaffold_files['metadata'] = files
            self._metadata_views = metadata_views

        def get_metadata_files(self):
            return self._scaffold_files['metadata']
        
        def get_metadata_children_files(self):
            return self._metadata_views

        def set_view_files(self, files):
            self._scaffold_files['view'] = files

        def get_view_files(self):
            return self._scaffold_files['view']

        def set_thumbnail_files(self, files):
            self._scaffold_files['thumbnail'] = files

        def get_thumbnail_files(self):
            return self._scaffold_files['thumbnail']

    def get_scaffold_data(self):
        return self._scaffold

    def setup_dataset(self, dataset_dir, max_size):
        self._scaffold = OnDiskFiles.Scaffold()
        metadata_file, metadata_views = search_for_metadata_files(dataset_dir, max_size)
        self._scaffold.set_metadate_files(metadata_file, metadata_views)
        self._scaffold.set_view_files(search_for_view_files(dataset_dir, max_size))
        self._scaffold.set_thumbnail_files(search_for_thumbnail_files(dataset_dir))
        return self

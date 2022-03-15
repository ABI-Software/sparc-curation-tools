import json
import os
from pathlib import Path

from sparc.curation.tools.definitions import CONTEXT_INFO_MIME
from sparc.curation.tools.manifests import ManifestDataFrame
from sparc.curation.tools.ondisk import is_json_of_type, is_csv_of_type, is_context_data_file, is_annotation_csv_file


def get_dataset_dir():
    return ManifestDataFrame().get_dataset_dir()


def get_context_info_file():
    dataset_dir = ManifestDataFrame().get_dataset_dir()
    context_info_dir = dataset_dir
    if os.path.exists(os.path.join(dataset_dir, "files")):
        dataset_dir = os.path.join(dataset_dir, "files")
    if os.path.exists(os.path.join(dataset_dir, "derivative")):
        context_info_dir = os.path.join(dataset_dir, "derivative")
    return os.path.join(context_info_dir, "scaffold_context_info.json")


def get_context_info_dir():
    return os.path.dirname(get_context_info_file())


def write_context_info(context_info_location, data):
    with open(context_info_location, 'w') as outfile:
        json.dump(data, outfile, default=lambda o: o.__dict__, sort_keys=True, indent=2)


def update_additional_type(file_location):
    ManifestDataFrame().update_additional_type(file_location, CONTEXT_INFO_MIME)


def update_supplemental_json(file_location, annotation_data):
    ManifestDataFrame().update_supplemental_json(file_location, annotation_data)


def update_anatomical_entity(file_location, annotation_data):
    ManifestDataFrame().update_anatomical_entity(file_location, annotation_data)


def search_for_context_data_files(dataset_dir, max_size):
    context_data_files = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        _is_context_data_file = is_json_of_type(r, max_size, is_context_data_file)
        if _is_context_data_file:
            context_data_files.append(r)

    return context_data_files


def search_for_annotation_csv_files(dataset_dir, max_size):
    annotation_csv_files = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        _is_annotation_csv_file = is_csv_of_type(r, max_size, is_annotation_csv_file)
        if _is_annotation_csv_file:
            annotation_csv_files.append(r)

    return annotation_csv_files

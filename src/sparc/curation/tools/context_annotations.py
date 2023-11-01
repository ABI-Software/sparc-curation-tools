import json
import os
from pathlib import Path

from sparc.curation.tools.errors import DatasetNotDefinedError
from sparc.curation.tools.utilities import get_absolute_path
from sparc.curation.tools.definitions import CONTEXT_INFO_MIME, DERIVED_FROM_COLUMN, SOURCE_OF_COLUMN
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.helpers.file_helper import is_json_of_type, is_csv_of_type, is_context_data_file, is_annotation_csv_file


def get_dataset_dir():
    return OnDiskFiles().get_dataset_dir()


def update_context_info(context_info):
    context_info_location = get_absolute_path(get_dataset_dir(), context_info.get_filename())
    write_context_info(context_info_location, context_info.as_dict())


def annotate_context_info(context_info):
    if not OnDiskFiles().is_defined():
        raise DatasetNotDefinedError()

    context_info_location = get_absolute_path(get_dataset_dir(), context_info.get_filename())
    metadata_location = get_absolute_path(get_dataset_dir(), context_info.get_metadata_file())
    annotation_data = create_annotation_data_json(context_info.get_views(), context_info.get_samples())
    update_additional_type(context_info_location)
    update_supplemental_json(context_info_location, json.dumps(annotation_data))
    update_derived_from_entity(context_info_location, os.path.basename(context_info.get_metadata_file()))
    update_parent_source_of_entity(os.path.basename(context_info_location), metadata_location)


def create_annotation_data_json(views, samples):
    annotation_data = {
        "version": "0.2.0",
        "id": "sparc.science.annotation_terms",
    }

    def _add_entry(_annotation_data, annotation, value):
        if annotation and annotation != "--":
            if annotation in _annotation_data:
                _annotation_data[annotation].append(value)
            else:
                _annotation_data[annotation] = [value]

    for v in views:
        _add_entry(annotation_data, v["annotation"], v["id"])
        if v["annotation"] != "--":
            update_anatomical_entity(get_absolute_path(get_dataset_dir(), v["path"]), v["annotation"])

    for s in samples:
        _add_entry(annotation_data, s["annotation"], s["id"])

    return annotation_data


def write_context_info(context_info_location, data):
    with open(context_info_location, 'w') as outfile:
        json.dump(data, outfile, default=lambda o: o.__dict__, sort_keys=True, indent=2)


def update_additional_type(file_location):
    ManifestDataFrame().update_additional_type(file_location, CONTEXT_INFO_MIME)


def update_supplemental_json(file_location, annotation_data):
    ManifestDataFrame().update_supplemental_json(file_location, annotation_data)


def update_anatomical_entity(file_location, annotation_data):
    ManifestDataFrame().update_anatomical_entity(file_location, annotation_data)


def update_parent_source_of_entity(file_location, parent_location):
    ManifestDataFrame().update_column_content(parent_location, SOURCE_OF_COLUMN, file_location, True)


def update_derived_from_entity(file_location, parent_location):
    ManifestDataFrame().update_column_content(file_location, DERIVED_FROM_COLUMN, parent_location)


def search_for_annotation_csv_files(dataset_dir, max_size):
    annotation_csv_files = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        _is_annotation_csv_file = is_csv_of_type(r, max_size, is_annotation_csv_file)
        if _is_annotation_csv_file:
            annotation_csv_files.append(r)

    return annotation_csv_files

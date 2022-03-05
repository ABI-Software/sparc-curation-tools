import argparse
import os
import json
import pandas as pd

from sparc.curation.tools.definitions import ADDITIONAL_TYPES_COLUMN, SUPPLEMENTAL_JSON_COLUMN, CONTEXT_INFO_MIME
from sparc.curation.tools.errors import AnnotationDirectoryNoWriteAccess
from sparc.curation.tools.manifests import ManifestDataFrame
from sparc.curation.tools.ondisk import OnDiskFiles
from sparc.curation.tools.utilities import convert_to_bytes, is_same_file


def read_context_info(contextinfo_location, data):
    with open(contextinfo_location, 'r') as outfile:
        data = json.load(outfile, default=lambda o: o.__dict__, sort_keys=True, indent=2)
    return data

def write_context_info(contextinfo_location, data):
    with open(contextinfo_location, 'w') as outfile:
        json.dump(data, outfile, default=lambda o: o.__dict__, sort_keys=True, indent=2)

def update_additional_type(file_location):
    ManifestDataFrame().update_additional_type(file_location, CONTEXT_INFO_MIME)

def update_supplemental_json(file_location, annotation_data):
    ManifestDataFrame().update_supplemental_json(file_location, annotation_data)

def update_anatomical_entity(file_location, annotation_data):
    ManifestDataFrame().update_anatomical_entity(file_location, annotation_data)
import os

from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, MANIFEST_DIR_COLUMN, FILENAME_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, DERIVED_FROM_COLUMN


class ContextInfoAnnotation(object):

    def __init__(self, metadata_file, filename):
        self._metadata_file = metadata_file
        self._fileName = filename
        self._context_heading = ""
        self._banner = ""
        self._context_description = ""
        self._samples = []
        self._views = []

    def from_dict(self, data):
        self._metadata_file = data["metadata"] if "metadata" in data else ""
        self._context_heading = data["heading"] if "heading" in data else ""
        self._banner = data["banner"] if "banner" in data else ""
        self._context_description = data["description"] if "description" in data else ""
        self._samples = data["samples"] if "samples" in data else ""
        self._views = data["views"] if "views" in data else ""

    def get_context_json(self):
        data = {
            "version": "0.2.0",
            "id": "sparc.science.context_data",
            "metadata": self._metadata_file,
            "heading": self._context_heading,
            "banner": self._banner,
            "description": self._context_description,
            "samples": self._samples,
            "views": self._views,
        }
        return data

    def get_views(self):
        return self._views

    def get_samples(self):
        return self._samples

    def __eq__(self, other):
        return os.path.samefile(self.get_location(), other.get_location())

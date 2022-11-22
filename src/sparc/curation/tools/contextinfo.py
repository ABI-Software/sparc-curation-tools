import os

from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, MANIFEST_DIR_COLUMN, FILENAME_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, DERIVED_FROM_COLUMN


class ContextInfoAnnotation(object):
    """
    TODO
    """

    def __init__(self, metadata_file, filename):
        self._metadata_file = metadata_file
        self._fileName = filename
        self._context_heading = ""
        self._context_description = ""
        self._samples = []
        self._views = []

    def from_dict(self, data):
        self._metadata_file = data["metadata"]
        self._context_heading = data["heading"]
        self._context_description = data["description"]
        self._samples = data["samples"]
        self._views = data["views"]

    def get_context_json(self):
        data = {
            "version": "0.1.0",
            "id": "sparc.science.context_data",
            "metadata": self._metadata_file,
            "heading": self._context_heading,
            "description": self._context_description,
            "samples": self._samples,
            "views": self._views,
        }
        return data

    def __eq__(self, other):
        return os.path.samefile(self.get_location(), other.get_location())

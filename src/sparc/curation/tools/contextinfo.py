import os

from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, MANIFEST_DIR_COLUMN, FILENAME_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, DERIVED_FROM_COLUMN


class ContextInfoAnnotation(object):
    """
    TODO use this class to wrap one dataframe row to an object.
    Only rows with ADDITIONAL_TYPES_COLUMN will be wrapped by this class
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

    def get_annotation_data_json(self):
        annotation_data = {
            "version": "0.2.0",
            "id": "sparc.science.annotation_data",
        }

        def _add_entry(_annotation_data, annotation, value):
            if annotation and annotation != "--":
                if annotation in _annotation_data:
                    _annotation_data[annotation].append(value)
                else:
                    _annotation_data[annotation] = [value]

        for v in self._views:
            _add_entry(annotation_data, v["annotation"], v["id"])
            if v["annotation"] != "--":
                context_annotations.update_anatomical_entity(os.path.join(self._location, v["path"]), v["annotation"])

        for s in self._samples:
            _add_entry(annotation_data, s["annotation"], s["id"])
        
        return annotation_data

    def __eq__(self, other):
        return os.path.samefile(self.get_location(), other.get_location())

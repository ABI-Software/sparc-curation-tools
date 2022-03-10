import os

from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, MANIFEST_DIR_COLUMN, FILENAME_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, DERIVED_FROM_COLUMN


class ScaffoldAnnotation(object):
    """
    TODO use this class to wrap one dataframe row to an object.
    Only rows with ADDITIONAL_TYPES_COLUMN will be wrapped by this class
    """

    def __init__(self, dataframe_row):
        self._dir = dataframe_row[FILE_LOCATION_COLUMN]  # This is now redundant.
        self._manifestDir = dataframe_row[MANIFEST_DIR_COLUMN]
        self._fileName = dataframe_row[FILENAME_COLUMN]
        self._location = dataframe_row[FILE_LOCATION_COLUMN]
        self._additionalType = None
        self._children = []
        self._parent = []

        if ADDITIONAL_TYPES_COLUMN in dataframe_row:
            if isinstance(dataframe_row[ADDITIONAL_TYPES_COLUMN], str):
                self._additionalType = dataframe_row[ADDITIONAL_TYPES_COLUMN]

        if SOURCE_OF_COLUMN in dataframe_row:
            if isinstance(dataframe_row[SOURCE_OF_COLUMN], str):
                self._children = [str(os.path.join(self._manifestDir, filename)) for filename in dataframe_row[SOURCE_OF_COLUMN].split(',')]

        if DERIVED_FROM_COLUMN in dataframe_row:
            if isinstance(dataframe_row[DERIVED_FROM_COLUMN], str):
                self._parent = str(os.path.join(self._manifestDir, dataframe_row[DERIVED_FROM_COLUMN]))
                # Is it possible one file can have multiple derivedFrom files
                # self._parent = [str(os.path.join(self._manifestDir, filename)) for filename in dataframe_row[DERIVED_FROM_COLUMN].split(',')]

    def get_location(self):
        return os.path.normpath(os.path.join(self._location))

    def get_additional_type(self):
        return self._additionalType

    def set_dir(self, dir_name):
        self._dir = dir_name

    def get_dir(self):
        return self._dir

    def set_filename(self, file):
        self._fileName = file

    def get_filename(self):
        return self._fileName

    def get_children(self):
        return self._children

    def get_parent(self):
        return self._parent

    def get_thumbnail(self):
        return self._children[0]

    def __eq__(self, other):
        return os.path.samefile(self.get_location(), other.get_location())

import os

from sparc.curation.tools.definitions import MIMETYPE_TO_FILETYPE_MAP, MIMETYPE_TO_PARENT_FILETYPE_MAP, MIMETYPE_TO_CHILDREN_FILETYPE_MAP, FILE_LOCATION_COLUMN, MANIFEST_DIR_COLUMN, FILENAME_COLUMN, ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, \
    DERIVED_FROM_COLUMN


class ScaffoldAnnotationError(object):

    def __init__(self, message, location, mime):
        self._message = message
        self._location = location
        self._mime = mime

    def get_location(self):
        return self._location

    def get_error_message(self):
        return f'Error: {self._message}'

    def get_mime(self):
        return self._mime

    # def __str__(self):
    #     return f'Error: {self._message}'


class NotAnnotatedError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found Scaffold '{fileType}' file that is not annotated '{location}'."
        super(NotAnnotatedError, self).__init__(message, location, mime)

class IncorrectSourceOfError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        childrenFileType = MIMETYPE_TO_CHILDREN_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found '{fileType}' file '{location}' either has no {childrenFileType} file or it's annotated to an incorrect file."
        super(IncorrectSourceOfError, self).__init__(message, location, mime)

class IncorrectDerivedFromError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        parentFileType = MIMETYPE_TO_PARENT_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found '{fileType}' file '{location}' either has no derived from file or it's not derived from a scaffold '{parentFileType}' file."
        super(IncorrectDerivedFromError, self).__init__(message, location, mime)

class IncorrectAnnotationError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        message = f"File '{location}' either does not exist or is not a scaffold '{fileType}' file."
        super(IncorrectAnnotationError, self).__init__(message, location, mime)

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
        self._children = None
        self._parent = None

        if ADDITIONAL_TYPES_COLUMN in dataframe_row:
            if isinstance(dataframe_row[ADDITIONAL_TYPES_COLUMN], str):
                self._additionalType = dataframe_row[ADDITIONAL_TYPES_COLUMN]

        if SOURCE_OF_COLUMN in dataframe_row:
            if isinstance(dataframe_row[SOURCE_OF_COLUMN], str):
                self._children = [str(os.path.join(self._manifestDir, filename)) for filename in dataframe_row[SOURCE_OF_COLUMN].split(',')]

        if DERIVED_FROM_COLUMN in dataframe_row:
            if isinstance(dataframe_row[DERIVED_FROM_COLUMN], str):
                self._parent = str(os.path.join(self._manifestDir, dataframe_row[DERIVED_FROM_COLUMN]))

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

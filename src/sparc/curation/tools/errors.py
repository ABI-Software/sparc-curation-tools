from sparc.curation.tools.definitions import MIMETYPE_TO_FILETYPE_MAP, MIMETYPE_TO_PARENT_FILETYPE_MAP, MIMETYPE_TO_CHILDREN_FILETYPE_MAP


class ScaffoldAnnotationError(object):
    """
    Base class for scaffold annotation errors.

    Attributes:
        _message (str): Error message.
        _location (str): Location of the file.
        _mime (str): MIME type of the file.
    """

    def __init__(self, message, location, mime):
        """
        Initialize the ScaffoldAnnotationError object.

        Args:
            message (str): Error message.
            location (str): Location of the file.
            mime (str): MIME type of the file.
        """
        self._message = message
        self._location = location
        self._mime = mime

    def get_location(self):
        """
        Get the location of the file.

        Returns:
            str: File location.
        """
        return self._location

    def get_error_message(self):
        """
        Get the error message.

        Returns:
            str: Error message.
        """
        return f'Error: {self._message}'

    def get_mime(self):
        """
        Get the MIME type of the file.

        Returns:
            str: MIME type.
        """
        return self._mime

    def __eq__(self, other):
        """
        Check if two ScaffoldAnnotationError objects are equal.

        Args:
            other (ScaffoldAnnotationError): Another object to compare.

        Returns:
            bool: True if equal, False otherwise.
        """
        return (
            self._mime == other.get_mime()
            and self._location == other.get_location()
            and self.get_error_message() == other.get_error_message()
        )


class OldAnnotationError(ScaffoldAnnotationError):
    """
    Class for errors related to old annotations.
    Inherits from ScaffoldAnnotationError.
    """

    def __init__(self, location, mime):
        """
        Initialize the OldAnnotationError object.

        Args:
            location (str): Location of the file.
            mime (str): MIME type of the file.
        """
        message = f"Found old annotation '{mime}'"
        super(OldAnnotationError, self).__init__(message, location, mime)


class NotAnnotatedError(ScaffoldAnnotationError):
    """
    Class for errors related to missing annotations.
    Inherits from ScaffoldAnnotationError.
    """

    def __init__(self, location, mime):
        """
        Initialize the NotAnnotatedError object.

        Args:
            location (str): Location of the file.
            mime (str): MIME type of the file.
        """
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found Scaffold '{fileType}' file that is not annotated '{location}'."
        super(NotAnnotatedError, self).__init__(message, location, mime)


class IncorrectBaseError(ScaffoldAnnotationError):
    """
    Base class for errors related to incorrect base files.
    Inherits from ScaffoldAnnotationError.
    """

    def __init__(self, message, location, mime, target, replace=False):
        """
        Initialize the IncorrectBaseError object.

        Args:
            message (str): Error message.
            location (str): Location of the file.
            mime (str): MIME type of the file.
            target (str): Target file.
        """
        super(IncorrectBaseError, self).__init__(message, location, mime)
        self._target = target
        self._replace = replace

    def get_target(self):
        """
        Get the target file.

        Returns:
            str: Target file.
        """
        return self._target

    def get_replace(self):
        """
        Get the replace state.

        Returns:
            bool: state
        """
        return self._replace

    def __eq__(self, other):
        """
        Check if two IncorrectBaseError objects are equal.

        Args:
            other (IncorrectBaseError): Another object to compare.

        Returns:
            bool: True if equal, False otherwise.
        """
        if super(IncorrectBaseError, self).__eq__(other):
            return self._target == other.get_target()

        return False


class IncorrectSourceOfError(IncorrectBaseError):
    """
    Class for errors related to incorrect source files.
    Inherits from IncorrectBaseError.
    """

    def __init__(self, location, mime, target, replace=False):
        """
        Initialize the IncorrectSourceOfError object.

        Args:
            location (str): Location of the file.
            mime (str): MIME type of the file.
            target (str): Target file.
            replace (bool): If removing an incorrect source of replace with current content.
        """
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        childrenFileType = ', '.join(MIMETYPE_TO_CHILDREN_FILETYPE_MAP.get(mime, 'unknown'))
        message = f"Found '{fileType}' file '{location}' either has no {childrenFileType} file or it's annotated to " \
                  f"an incorrect file. "
        super(IncorrectSourceOfError, self).__init__(message, location, mime, target, replace)


class IncorrectDerivedFromError(IncorrectBaseError):
    """
    Class for errors related to incorrect derived from files.
    Inherits from IncorrectBaseError.
    """

    def __init__(self, location, mime, target):
        """
        Initialize the IncorrectDerivedFromError object.

        Args:
            location (str): Location of the file.
            mime (str): MIME type of the file.
            target (str): Target file.
        """
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        parentFileType = MIMETYPE_TO_PARENT_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found '{fileType}' file '{location}' either has no derived from file or it's not derived from a " \
                  f"scaffold '{parentFileType}' file. "
        super(IncorrectDerivedFromError, self).__init__(message, location, mime, target)


class IncorrectAnnotationError(ScaffoldAnnotationError):
    """
    Class for errors related to incorrect annotations.
    Inherits from ScaffoldAnnotationError.
    """

    def __init__(self, location, mime):
        """
        Initialize the IncorrectAnnotationError object.

        Args:
            location (str): Location of the file.
            mime (str): MIME type of the file.
        """
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        message = f"File '{location}' either does not exist or is not a scaffold '{fileType}' file."
        super(IncorrectAnnotationError, self).__init__(message, location, mime)


class AnnotationError(Exception):
    """
    Base class for annotation errors.
    Inherits from Exception.
    """
    pass


class AnnotationDirectoryNoWriteAccess(AnnotationError):
    """
    Class for errors related to write access in the annotation directory.
    Inherits from AnnotationError.
    """
    pass


class BadManifestError(Exception):
    """
    Class for errors related to bad manifest.
    Inherits from Exception.
    """
    pass


class DatasetNotDefinedError(AnnotationError):
    """
    Class for errors where the dataset for annotations has not
    been defined.
    """
    pass

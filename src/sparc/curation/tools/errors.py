from sparc.curation.tools.definitions import MIMETYPE_TO_FILETYPE_MAP, MIMETYPE_TO_PARENT_FILETYPE_MAP, MIMETYPE_TO_CHILDREN_FILETYPE_MAP


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


class IncorrectBaseError(ScaffoldAnnotationError):

    def __init__(self, message, location, mime, target):
        super(IncorrectBaseError, self).__init__(message, location, mime)
        self._target = target

    def get_target(self):
        return self._target


class IncorrectSourceOfError(IncorrectBaseError):
    def __init__(self, location, mime, target):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        childrenFileType = MIMETYPE_TO_CHILDREN_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found '{fileType}' file '{location}' either has no {childrenFileType} file or it's annotated to an incorrect file."
        super(IncorrectSourceOfError, self).__init__(message, location, mime, target)


class IncorrectDerivedFromError(IncorrectBaseError):
    def __init__(self, location, mime, target):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        parentFileType = MIMETYPE_TO_PARENT_FILETYPE_MAP.get(mime, 'unknown')
        message = f"Found '{fileType}' file '{location}' either has no derived from file or it's not derived from a scaffold '{parentFileType}' file."
        super(IncorrectDerivedFromError, self).__init__(message, location, mime, target)


class IncorrectAnnotationError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        fileType = MIMETYPE_TO_FILETYPE_MAP.get(mime, 'unknown')
        message = f"File '{location}' either does not exist or is not a scaffold '{fileType}' file."
        super(IncorrectAnnotationError, self).__init__(message, location, mime)


class AnnotationError(Exception):
    pass


class AnnotationDirectoryNoWriteAccess(AnnotationError):
    pass


class BadManifestError(Exception):
    pass

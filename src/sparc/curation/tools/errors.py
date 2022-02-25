

class AnnotationError(Exception):
    pass


class AnnotationDirectoryNoWriteAccess(AnnotationError):
    pass


class BadManifestError(Exception):
    pass

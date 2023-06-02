class ScaffoldAnnotations(object):
    """
    Only rows with ADDITIONAL_TYPES_COLUMN will be wrapped by this class
    """

    def __init__(self, parent):
        self._additionalType = None
        self._children = []
        self._parent = parent

    def get_metadata_filenames(self):
        return self._parent.scaffold_get_metadata_files()

    def get_filename(self, source):
        return self._parent.get_filename(source)

    def get_plot_filenames(self):
        return self._parent.scaffold_get_plot_files()

    def get_derived_from_filenames(self, source):
        return self._parent.get_derived_from(source)

    def get_source_of_filenames(self, source):
        return self._parent.get_source_of(source)

    def get_manifest_directory(self, source):
        return self._parent.get_manifest_directory(source)[0]

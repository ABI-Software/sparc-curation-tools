import os

from sparc.curation.tools.definitions import MIMETYPE_TO_FILETYPE_MAP, MIMETYPE_TO_PARENT_FILETYPE_MAP, MIMETYPE_TO_CHILDREN_FILETYPE_MAP, FILE_LOCATION_COLUMN, MANIFEST_DIR_COLUMN, FILENAME_COLUMN, ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, \
    DERIVED_FROM_COLUMN

class ContextInfo(object):
    """
    {
        "description": "",
        "heading": "",
        "samples": [],
        "version": "0.1.0",
        "views": [
            {
            "annotation": "UBERON:0001155",
            "id": "View 1",
            "path": "C:/Users/ywan787/neondata/aaa/exports/mouseColon_view.json",
            "sample": "--",
            "thumbnail": "C:/Users/ywan787/neondata/aaa/exports/proximalColon_thumbnail.png"
            },
            {
            "annotation": "UBERON:0008971",
            "id": "View 2",
            "path": "C:/Users/ywan787/neondata/aaa/exports/proximalColon_view.json",
            "sample": "--",
            "thumbnail": ""
            }
        ]
    }
    """

    def __init__(self, dictInput):
        self._manifestDir = None
        self._description = None
        self._heading = None
        self._version = None
        self._samples = []
        self._views = []
        self._deserialize(dictInput)

    def _deserialize(self, dictInput):
        # convert to absolute file path so can save Neon file to new location and get correct relative path
        if "description" in dictInput:
            self._description = dictInput["description"]
        if "heading" in dictInput:
            self._heading = dictInput["heading"]
        if "samples" in dictInput:
            self._samples = dictInput["samples"]
        if "version" in dictInput:
            self._version = dictInput["version"]
        if "views" in dictInput:
            self._views = dictInput["views"]

    def serialize(self, basePath=None):
        dictOutput = {}
        dictOutput["Type"] = self.getType()
        dictOutput["FileName"] = fileNameToRelativePath(self._fileName, basePath)
        if self._region_name is not None:
            dictOutput["RegionName"] = self._region_name
        if self._time is not None:
            dictOutput["Time"] = self._time
        if self._edit:
            dictOutput["Edit"] = True
        return dictOutput

    def set_description(self, description):
        self._description = description

    def get_description(self):
        return self._description

    def set_heading(self, heading):
        self._heading = heading

    def get_heading(self):
        return self._heading

    def set_samples(self, samples):
        self._samples = samples

    def get_samples(self):
        return self._samples

    def set_version(self, version):
        self._version = version

    def get_version(self):
        return self._version

    def set_views(self, view):
        self._views = view

    def get_views(self):
        return self._views
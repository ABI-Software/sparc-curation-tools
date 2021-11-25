import os
from pathlib import Path

import pandas as pd
from sparc.curation.tools.annotations.scaffold import ScaffoldAnnotation, IncorrectAnnotationError, NotAnnotatedError, IncorrectDerivedFromError, IncorrectSourceOfError

from sparc.curation.tools.base import Singleton
from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, FILENAME_COLUMN, ADDITIONAL_TYPES_COLUMN, SCAFFOLD_FILE_MIME, SCAFFOLD_VIEW_MIME, SCAFFOLD_THUMBNAIL_MIME, SCAFFOLD_DIR_MIME


class ManifestDataFrame(metaclass=Singleton):
    # dataFrame_dir = ""
    _manifestDataFrame = None
    _scaffold_data = None

    def setup_dataframe(self, dataset_dir):
        self.read_manifest(dataset_dir)
        self.setup_data()
        return self

    def read_manifest(self, dataset_dir):
        result = list(Path(dataset_dir).rglob("manifest.xlsx"))
        self._manifestDataFrame = pd.DataFrame()
        for r in result:
            xl_file = pd.ExcelFile(r)
            for sheet_name in xl_file.sheet_names:
                currentDataFrame = xl_file.parse(sheet_name)
                currentDataFrame['sheet_name'] = sheet_name
                currentDataFrame['manifest_dir'] = os.path.dirname(r)
                self._manifestDataFrame = pd.concat([currentDataFrame, self._manifestDataFrame])

        if not self._manifestDataFrame.empty:
            self._manifestDataFrame[FILE_LOCATION_COLUMN] = self._manifestDataFrame.apply(
                lambda row: os.path.join(row['manifest_dir'], row[FILENAME_COLUMN]) if pd.notnull(row[FILENAME_COLUMN]) else None, axis=1)
        return self._manifestDataFrame

    def get_manifest(self):
        return self._manifestDataFrame

    def create_manifest(self, manifest_dir):
        self._manifestDataFrame[FILENAME_COLUMN] = ''
        self._manifestDataFrame[FILE_LOCATION_COLUMN] = ''
        self._manifestDataFrame['manifest_dir'] = manifest_dir

    def setup_data(self):
        self._scaffold_data = ManifestDataFrame.Scaffold()
        try:
            self._scaffold_data.set_scaffold_annotations(
                [ScaffoldAnnotation(row) for i, row in self._manifestDataFrame[self._manifestDataFrame[ADDITIONAL_TYPES_COLUMN].notnull()].iterrows()]
            )
        except KeyError:
            pass
        self._scaffold_data.set_scaffold_locations([i.get_location() for i in self._scaffold_data.get_scaffold_annotations()])

    def get_scaffold_data(self):
        return self._scaffold_data

    class Scaffold(object):
        _data = {
            'annotations': [],
            'locations': [],
        }

        def set_scaffold_annotations(self, annotations):
            self._data['annotations'] = annotations

        def get_scaffold_annotations(self):
            return self._data['annotations']

        def set_scaffold_locations(self, locations):
            self._data['locations'] = locations

        def get_scaffold_locations(self):
            return self._data['locations']

        def get_metadata_filenames(self):
            filenames = []
            for i in self._data['annotations']:
                if i.get_additional_type() == SCAFFOLD_FILE_MIME:
                    filenames.append(i.get_location())

            return filenames

        def get_derived_filenames(self, source):
            for i in self._data['annotations']:
                if i.get_location() == source:
                    return i.get_children()
                # if i.get_parent() == source:
                #     return i.get_location()

            return []

        def get_missing_annotations(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            for i in on_disk_metadata_files:
                if i not in self._data['locations']:
                    errors.append(NotAnnotatedError(i, SCAFFOLD_FILE_MIME))

            for i in on_disk_view_files:
                if i not in self._data['locations']:
                    errors.append(NotAnnotatedError(i, SCAFFOLD_VIEW_MIME))

            for i in on_disk_thumbnail_files:
                if i not in self._data['locations']:
                    errors.append(NotAnnotatedError(i, SCAFFOLD_THUMBNAIL_MIME))

            return errors

        def get_incorrect_annotations(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            for i in self._data['annotations']:
                if i.get_additional_type() == SCAFFOLD_FILE_MIME:
                    if i.get_location() not in on_disk_metadata_files:
                        errors.append(IncorrectAnnotationError(i.get_location(), i.get_additional_type()))

                if i.get_additional_type() == SCAFFOLD_VIEW_MIME:
                    if i.get_location() not in on_disk_view_files:
                        errors.append(IncorrectAnnotationError(i.get_location(), i.get_additional_type()))

                if i.get_additional_type() == SCAFFOLD_THUMBNAIL_MIME:
                    if i.get_location() not in on_disk_thumbnail_files:
                        errors.append(IncorrectAnnotationError(i.get_location(), i.get_additional_type()))
                
                if i.get_additional_type() == SCAFFOLD_DIR_MIME:
                    errors.append(IncorrectAnnotationError(i.get_location(), i.get_additional_type()))
            return errors

        def get_incorrect_derived_from(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            for i in self._data['annotations']:

                if i.get_additional_type() == SCAFFOLD_VIEW_MIME:
                    if i.get_location() in on_disk_view_files and i.get_parent() not in on_disk_metadata_files:
                        errors.append(IncorrectDerivedFromError(i.get_location(), SCAFFOLD_VIEW_MIME))

                if i.get_additional_type() == SCAFFOLD_THUMBNAIL_MIME:
                    if i.get_location() in on_disk_thumbnail_files and i.get_parent() not in on_disk_view_files:
                        errors.append(IncorrectDerivedFromError(i.get_location(), SCAFFOLD_THUMBNAIL_MIME))

            return errors

        def get_incorrect_source_of(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_metadata_children_files = on_disk.get_scaffold_data().get_metadata_children_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            for i in self._data['annotations']:

                if i.get_additional_type() == SCAFFOLD_FILE_MIME:
                    if i.get_location() in on_disk_metadata_files:
                        if not i.get_children():
                            errors.append(IncorrectSourceOfError(i.get_location(), SCAFFOLD_FILE_MIME))
                        elif not set(i.get_children()) == set(on_disk_metadata_children_files[i.get_location()]):
                            errors.append(IncorrectSourceOfError(i.get_location(), SCAFFOLD_FILE_MIME))

                if i.get_additional_type() == SCAFFOLD_VIEW_MIME:
                    # Program to check the on_disk_thumbnail_files list contains all elements of i.get_children()
                    if i.get_location() in on_disk_view_files:
                        if not i.get_children():
                            errors.append(IncorrectSourceOfError(i.get_location(), SCAFFOLD_VIEW_MIME))
                        elif not all(item in on_disk_thumbnail_files for item in i.get_children()):
                            errors.append(IncorrectSourceOfError(i.get_location(), SCAFFOLD_VIEW_MIME))

            return errors
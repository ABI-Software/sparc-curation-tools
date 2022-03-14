import os
import re
from pathlib import Path

import pandas as pd

from sparc.curation.tools.errors import IncorrectAnnotationError, NotAnnotatedError, IncorrectDerivedFromError, \
    IncorrectSourceOfError, BadManifestError
from sparc.curation.tools.base import Singleton
from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, FILENAME_COLUMN, SUPPLEMENTAL_JSON_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, ANATOMICAL_ENTITY_COLUMN, SCAFFOLD_META_MIME, SCAFFOLD_VIEW_MIME, \
    SCAFFOLD_THUMBNAIL_MIME, SCAFFOLD_DIR_MIME, DERIVED_FROM_COLUMN, SOURCE_OF_COLUMN, MANIFEST_DIR_COLUMN, MANIFEST_FILENAME, SHEET_NAME_COLUMN
from sparc.curation.tools.utilities import is_same_file


class ManifestDataFrame(metaclass=Singleton):
    # dataFrame_dir = ""
    _manifestDataFrame = None
    _scaffold_data = None
    _dataset_dir = None

    def setup_dataframe(self, dataset_dir):
        self._dataset_dir = dataset_dir
        self._read_manifests()
        self._scaffold_data = ManifestDataFrame.Scaffold(self)
        return self

    def _read_manifests(self, depth=0):
        self._manifestDataFrame = pd.DataFrame()
        result = list(Path(self._dataset_dir).rglob(MANIFEST_FILENAME))
        for r in result:
            xl_file = pd.ExcelFile(r)
            for sheet_name in xl_file.sheet_names:
                currentDataFrame = xl_file.parse(sheet_name)
                currentDataFrame[SHEET_NAME_COLUMN] = sheet_name
                currentDataFrame[MANIFEST_DIR_COLUMN] = os.path.dirname(r)
                self._manifestDataFrame = pd.concat([currentDataFrame, self._manifestDataFrame])

        if not self._manifestDataFrame.empty:
            self._manifestDataFrame[FILE_LOCATION_COLUMN] = self._manifestDataFrame.apply(
                lambda row: os.path.join(row[MANIFEST_DIR_COLUMN], row[FILENAME_COLUMN]) if pd.notnull(row[FILENAME_COLUMN]) else None, axis=1)

        sanitised = self._sanitise_dataframe()
        if sanitised and depth == 0:
            self._read_manifests(depth + 1)
        elif sanitised and depth > 0:
            raise BadManifestError('Manifest sanitisation error found.')

    def get_manifest(self):
        return self._manifestDataFrame

    def create_manifest(self, manifest_dir):
        """
        " If there isn't any manifest file under dataset dir, create one
        """
        self._manifestDataFrame[FILENAME_COLUMN] = ''
        self._manifestDataFrame[FILE_LOCATION_COLUMN] = ''
        self._manifestDataFrame[MANIFEST_DIR_COLUMN] = manifest_dir

    def _sanitise_is_derived_from(self, column_names):
        sanitised = False
        bad_column_name = ''
        for column_name in column_names:
            if column_name.lower() == DERIVED_FROM_COLUMN.lower():
                if column_name != DERIVED_FROM_COLUMN:
                    bad_column_name = column_name

                break

        if bad_column_name:
            manifests = [row[MANIFEST_DIR_COLUMN] for i, row in self._manifestDataFrame[self._manifestDataFrame[bad_column_name].notnull()].iterrows()]
            unique_manifests = list(set(manifests))
            for manifest_dir in unique_manifests:
                current_manifest = os.path.join(manifest_dir, MANIFEST_FILENAME)
                mDF = pd.read_excel(current_manifest)
                mDF.rename(columns={bad_column_name: DERIVED_FROM_COLUMN}, inplace=True)
                mDF.to_excel(current_manifest, index=False, header=True)
                sanitised = True

        return sanitised

    def _sanitise_dataframe(self):
        column_names = self._manifestDataFrame.columns
        sanitised = self._sanitise_is_derived_from(column_names)
        return sanitised

    def get_scaffold_data(self):
        return self._scaffold_data

    def get_dataset_dir(self):
        return self._dataset_dir

    def _get_matching_dataframe(self, file_location):
        same_file = []

        for index, row in self._manifestDataFrame.iterrows():
            location = os.path.join(row[MANIFEST_DIR_COLUMN], row[FILENAME_COLUMN])
            same_file.append(is_same_file(file_location, location))

        return self._manifestDataFrame[same_file]

    def get_matching_entry(self, column_heading, value, out_column_heading=FILENAME_COLUMN):
        matching_files = []
        for index, row in self._manifestDataFrame.iterrows():
            if column_heading in row and row[column_heading] == value and out_column_heading in row:
                matching_files.append(row[out_column_heading])

        return matching_files

    def get_entry_that_includes(self, column_heading, value, out_column_heading=FILENAME_COLUMN):
        matching_files = []
        for index, row in self._manifestDataFrame.iterrows():
            if column_heading in row and isinstance(row[column_heading], str):
                if value in row[column_heading].split("\n") and out_column_heading in row:
                    matching_files.append(row[out_column_heading])

        return matching_files

    def get_filepath_on_disk(self, file_location):
        filenames = self.get_matching_entry(FILENAME_COLUMN, file_location, FILE_LOCATION_COLUMN)
        return filenames[0]

    def scaffold_get_metadata_files(self):
        return self.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_META_MIME)

    def get_derived_from(self, file_location):
        return self.get_matching_entry(DERIVED_FROM_COLUMN, file_location)

    def get_source_of(self, file_location):
        return self.get_entry_that_includes(SOURCE_OF_COLUMN, file_location)

    def get_file_dataframe(self, file_location):
        """
        Get file dataframe which match the file_location
        """
        manifestDataFrame = self._manifestDataFrame
        file_dir = os.path.dirname(file_location)
        file_name = os.path.basename(file_location)

        # Search data rows to find match to the same file by file_location.
        fileDF = self._get_matching_dataframe(file_location)

        # If fileDF is empty, means there's no manifest file containing this file's annotation.
        if fileDF.empty:
            newRow = pd.DataFrame({FILENAME_COLUMN: file_name}, index=[1])
            # Check if there's manifest file under same Scaffold File Dir. If yes get data from it.
            # If no manifest file create new manifest file. Add file to the manifest.
            if not manifestDataFrame[manifestDataFrame[MANIFEST_DIR_COLUMN] == file_dir].empty:
                mDF = pd.read_excel(os.path.join(file_dir, MANIFEST_FILENAME))
                newRow = mDF.concat(newRow, ignore_index=True)
            newRow.to_excel(os.path.join(file_dir, MANIFEST_FILENAME), index=False, header=True)

            # Re-read manifests to find dataframe for newly added entry.
            self._read_manifests()
            fileDF = self._get_matching_dataframe(file_location)

        return fileDF

    def update_additional_type(self, file_location, file_mime):
        self.update_column_content(file_location, ADDITIONAL_TYPES_COLUMN, file_mime)

    def update_supplemental_json(self, file_location, annotation_data):
        self.update_column_content(file_location, SUPPLEMENTAL_JSON_COLUMN, annotation_data)

    def update_anatomical_entity(self, file_location, annotation_data):
        self.update_column_content(file_location, ANATOMICAL_ENTITY_COLUMN, annotation_data)

    def update_column_content(self, file_location, column_name, content, append=False):
        # Update the cells with row: file_location, column: column_name to content
        fileDF = self.get_file_dataframe(file_location)
        for index, row in fileDF.iterrows():
            mDF = pd.read_excel(os.path.join(row[MANIFEST_DIR_COLUMN], MANIFEST_FILENAME), sheet_name=row[SHEET_NAME_COLUMN])
            if column_name not in mDF.columns:
                mDF[column_name] = ""

            if append:
                content = "\n".join([mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name], content])

            mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name] = content
            mDF.to_excel(os.path.join(row[MANIFEST_DIR_COLUMN], MANIFEST_FILENAME), sheet_name=row[SHEET_NAME_COLUMN], index=False, header=True)

    class Scaffold(object):

        def __init__(self, parent):
            self._parent = parent

        def update_derived_from(self, file_location, mime, target):
            source_manifest = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, file_location, MANIFEST_DIR_COLUMN)
            target_filenames = []
            if mime == SCAFFOLD_VIEW_MIME:
                for t in target:
                    target_manifest = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                    if source_manifest == target_manifest:
                        target_filenames.extend(self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN))

            elif mime == SCAFFOLD_THUMBNAIL_MIME:
                target_filenames = ["nothing matched"]
                for t in target:
                    target_manifest = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                    if source_manifest == target_manifest:
                        file_location_stub = re.sub(r"_thumbnail.jpeg$", "", file_location)
                        if t.startswith(file_location_stub):
                            target_filenames = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN)

            if len(target_filenames) == 0:
                target_filenames = ["failed to find a suitable source"]

            self._parent.update_column_content(file_location, DERIVED_FROM_COLUMN, "\n".join(target_filenames))

        def update_source_of(self, file_location, mime, target):
            source_manifest = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, file_location, MANIFEST_DIR_COLUMN)
            target_filenames = []
            if mime == SCAFFOLD_META_MIME:
                for t in target:
                    target_manifest = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                    if source_manifest == target_manifest:
                        target_filenames.extend(self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN))

            elif mime == SCAFFOLD_VIEW_MIME:
                target_filenames = ["nothing matched"]
                for t in target:
                    target_manifest = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                    if source_manifest == target_manifest:
                        file_location_stub = re.sub(r"_view.json$", "", file_location)
                        if t.startswith(file_location_stub):
                            target_filenames = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN)

            if len(target_filenames) == 0:
                target_filenames = ["failed to find a suitable source"]

            self._parent.update_column_content(file_location, SOURCE_OF_COLUMN, "\n".join(target_filenames))

        def get_metadata_filenames(self):
            return self._parent.scaffold_get_metadata_files()

        def get_derived_from_filenames(self, source):
            return self._parent.get_derived_from(source)

        def get_source_of_filenames(self, source):
            return self._parent.get_source_of(source)

        def get_missing_annotations(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            manifest_metadata_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_META_MIME, FILE_LOCATION_COLUMN)
            for i in on_disk_metadata_files:
                if i not in manifest_metadata_files:
                    errors.append(NotAnnotatedError(i, SCAFFOLD_META_MIME))

            manifest_view_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_VIEW_MIME, FILE_LOCATION_COLUMN)
            for i in on_disk_view_files:
                if i not in manifest_view_files:
                    errors.append(NotAnnotatedError(i, SCAFFOLD_VIEW_MIME))

            manifest_thumbnail_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_THUMBNAIL_MIME, FILE_LOCATION_COLUMN)
            for i in on_disk_thumbnail_files:
                if i not in manifest_thumbnail_files:
                    errors.append(NotAnnotatedError(i, SCAFFOLD_THUMBNAIL_MIME))

            return errors

        def get_incorrect_annotations(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            manifest_metadata_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_META_MIME, FILE_LOCATION_COLUMN)
            manifest_view_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_VIEW_MIME, FILE_LOCATION_COLUMN)
            manifest_thumbnail_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_THUMBNAIL_MIME, FILE_LOCATION_COLUMN)
            manifest_directory_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_DIR_MIME, FILE_LOCATION_COLUMN)

            for i in manifest_metadata_files:
                if i not in on_disk_metadata_files:
                    errors.append(IncorrectAnnotationError(i, SCAFFOLD_META_MIME))

            for i in manifest_view_files:
                if i not in on_disk_view_files:
                    errors.append(IncorrectAnnotationError(i, SCAFFOLD_VIEW_MIME))

            for i in manifest_thumbnail_files:
                if i not in on_disk_thumbnail_files:
                    errors.append(IncorrectAnnotationError(i, SCAFFOLD_THUMBNAIL_MIME))

            for i in manifest_directory_files:
                errors.append(IncorrectAnnotationError(i, SCAFFOLD_DIR_MIME))

            return errors

        def _process_incorrect_derived_from(self, on_disk_files, on_disk_parent_files, manifest_files, incorrect_mime):
            errors = []

            for i in manifest_files:
                manifest_derived_from = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, i, DERIVED_FROM_COLUMN)
                manifest_derived_from_files = []
                for j in manifest_derived_from:
                    derived_from_files = self._parent.get_matching_entry(FILENAME_COLUMN, j, FILE_LOCATION_COLUMN)
                    manifest_derived_from_files.extend(derived_from_files)

                if len(manifest_derived_from_files) == 0:
                    errors.append(IncorrectDerivedFromError(i, incorrect_mime, on_disk_parent_files))
                elif len(manifest_derived_from_files) == 1:
                    if i in on_disk_files and manifest_derived_from_files[0] not in on_disk_parent_files:
                        errors.append(IncorrectDerivedFromError(i, incorrect_mime, on_disk_parent_files))

            return errors

        def get_incorrect_derived_from(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            manifest_view_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_VIEW_MIME, FILE_LOCATION_COLUMN)
            manifest_thumbnail_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_THUMBNAIL_MIME, FILE_LOCATION_COLUMN)

            view_derived_from_errors = self._process_incorrect_derived_from(on_disk_view_files, on_disk_metadata_files, manifest_view_files, SCAFFOLD_VIEW_MIME)
            errors.extend(view_derived_from_errors)

            thumbnail_derived_from_errors = self._process_incorrect_derived_from(on_disk_thumbnail_files, on_disk_view_files, manifest_thumbnail_files, SCAFFOLD_THUMBNAIL_MIME)
            errors.extend(thumbnail_derived_from_errors)

            return errors

        def _process_incorrect_source_of(self, on_disk_files, on_disk_child_files, manifest_files, incorrect_mime):
            errors = []

            for i in manifest_files:
                if i in on_disk_files:
                    manifest_source_of = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, i, SOURCE_OF_COLUMN)
                    if len(manifest_source_of) == 0:
                        errors.append(IncorrectSourceOfError(i, incorrect_mime, on_disk_child_files))
                    elif len(manifest_source_of) == 1:
                        source_of_files_list = []
                        source_ofs = manifest_source_of[0].split("\n")
                        for source_of in source_ofs:
                            source_of_files = self._parent.get_matching_entry(FILENAME_COLUMN, source_of, FILE_LOCATION_COLUMN)
                            source_of_files_list.extend(source_of_files)

                        if not all([item in on_disk_child_files for item in source_of_files_list]):
                            errors.append(IncorrectSourceOfError(i, incorrect_mime, on_disk_child_files))

            return errors

        def get_incorrect_source_of(self, on_disk):
            errors = []

            on_disk_metadata_files = on_disk.get_scaffold_data().get_metadata_files()
            on_disk_view_files = on_disk.get_scaffold_data().get_view_files()
            on_disk_thumbnail_files = on_disk.get_scaffold_data().get_thumbnail_files()

            manifest_metadata_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_META_MIME, FILE_LOCATION_COLUMN)
            manifest_view_files = self._parent.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_VIEW_MIME, FILE_LOCATION_COLUMN)

            metadata_source_of_errors = self._process_incorrect_source_of(on_disk_metadata_files, on_disk_view_files, manifest_metadata_files, SCAFFOLD_META_MIME)
            errors.extend(metadata_source_of_errors)

            view_source_of_errors = self._process_incorrect_source_of(on_disk_view_files, on_disk_thumbnail_files, manifest_view_files, SCAFFOLD_VIEW_MIME)
            errors.extend(view_source_of_errors)

            return errors

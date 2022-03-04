import os
from pathlib import Path

import pandas as pd
from sparc.curation.tools.annotations.scaffold import ScaffoldAnnotation
from sparc.curation.tools.errors import IncorrectAnnotationError, NotAnnotatedError, IncorrectDerivedFromError, \
    IncorrectSourceOfError, BadManifestError

from sparc.curation.tools.base import Singleton
from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, FILENAME_COLUMN, SUPPLEMENTAL_JSON_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, ANATOMICAL_ENTITY_COLUMN, SCAFFOLD_META_MIME, SCAFFOLD_VIEW_MIME, \
    SCAFFOLD_THUMBNAIL_MIME, SCAFFOLD_DIR_MIME, DERIVED_FROM_COLUMN, SOURCE_OF_COLUMN, MANIFEST_DIR_COLUMN
from sparc.curation.tools.ondisk import OnDiskFiles

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
        # self.setup_data()
        return self

    def _read_manifests(self, depth=0):
        self._manifestDataFrame = pd.DataFrame()
        result = list(Path(self._dataset_dir).rglob("manifest.xlsx"))
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
        self._manifestDataFrame['manifest_dir'] = manifest_dir

    def _sanitise_is_derived_from(self, column_names):
        sanitised = False
        bad_column_name = ''
        for column_name in column_names:
            if column_name.lower() == DERIVED_FROM_COLUMN.lower():
                if column_name != DERIVED_FROM_COLUMN:
                    bad_column_name = column_name

                break

        if bad_column_name:
            manifests = [row['manifest_dir'] for i, row in self._manifestDataFrame[self._manifestDataFrame[bad_column_name].notnull()].iterrows()]
            unique_manifests = list(set(manifests))
            for manifest_dir in unique_manifests:
                current_manifest = os.path.join(manifest_dir, "manifest.xlsx")
                mDF = pd.read_excel(current_manifest)
                mDF.rename(columns={bad_column_name: DERIVED_FROM_COLUMN}, inplace=True)
                mDF.to_excel(current_manifest, index=False, header=True)
                sanitised = True

        return sanitised

    def _sanitise_dataframe(self):
        column_names = self._manifestDataFrame.columns
        sanitised = self._sanitise_is_derived_from(column_names)
        return sanitised

    def setup_data(self):
        self._scaffold_data = ManifestDataFrame.Scaffold(self)
        try:
            self._scaffold_data.set_scaffold_annotations(
                [ScaffoldAnnotation(row) for i, row in self._manifestDataFrame[self._manifestDataFrame[ADDITIONAL_TYPES_COLUMN].notnull()].iterrows()]
            )
        except KeyError:
            pass
        self._scaffold_data.set_scaffold_locations([i.get_location() for i in self._scaffold_data.get_scaffold_annotations()])

    def get_scaffold_data(self):
        return self._scaffold_data

    def get_dataset_dir(self):
        return self._dataset_dir

    def _get_matching_dataframe(self, file_location):
        same_file = []

        for index, row in self._manifestDataFrame.iterrows():
            location = os.path.join(row[MANIFEST_DIR_COLUMN], row["filename"])
            same_file.append(is_same_file(file_location, location))

        return self._manifestDataFrame[same_file]

    def get_matching_entry(self, column_heading, value, out_column_heading=FILENAME_COLUMN):
        matching_files = []
        for index, row in self._manifestDataFrame.iterrows():
            if row[column_heading] == value:
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
        return self.get_matching_entry(SOURCE_OF_COLUMN, file_location)

    def get_file_dataframe(self, file_location):
        """
        " Get file dataframe which match the file_location
        """
        manifestDataFrame = self._manifestDataFrame
        file_dir = os.path.dirname(file_location)
        file_name = os.path.basename(file_location)

        # Search data rows to find match to the same file by file_location.
        fileDF = self._get_matching_dataframe(file_location)

        # If fileDF is empty, means there's no manifest file containing this file's annotation.
        if fileDF.empty:
            newRow = pd.DataFrame({"filename": file_name}, index=[1])
            # Check if there's manifest file under same Scaffold File Dir. If yes get data from it.
            # If no manifest file create new manifest file. Add file to the manifest.
            if not manifestDataFrame[manifestDataFrame["manifest_dir"] == file_dir].empty:
                mDF = pd.read_excel(os.path.join(file_dir, "manifest.xlsx"))
                newRow = mDF.append(newRow, ignore_index=True)
            newRow.to_excel(os.path.join(file_dir, "manifest.xlsx"), index=False, header=True)

            # Re-read manifests to find dataframe for newly added entry.
            self._read_manifests()
            fileDF = self._get_matching_dataframe(file_location)

        return fileDF

    def update_source_of(self, file_location, mime):
        fileDF = self.get_file_dataframe(file_location)
        manifestDir = fileDF["manifest_dir"].iloc[0]

        mDF = pd.read_excel(os.path.join(manifestDir, "manifest.xlsx"))
        if SOURCE_OF_COLUMN not in mDF.columns:
            mDF[SOURCE_OF_COLUMN] = ""

        viewNames = ""
        childrenLocations = []
        if mime == SCAFFOLD_META_MIME:
            childrenLocations = OnDiskFiles().get_scaffold_data().get_metadata_children_files()[file_location]
            viewNames = [os.path.relpath(children, manifestDir) for children in childrenLocations]

        # Search thumbnail in dataframe with same manifest_dir as scafflod
        # If found, set it as isSourceOf
        # If not, search file 
        
        elif mime == SCAFFOLD_VIEW_MIME:
            sa = ManifestDataFrame().get_scaffold_data().get_scaffold_annotations()
            for i in sa:
                if i.get_parent() == file_location:
                    childrenLocations = i.get_location()
            if childrenLocations:
                viewNames = os.path.relpath(childrenLocations, manifestDir)
            else:
                childrenLocations = OnDiskFiles().get_scaffold_data().get_thumbnail_files()
                viewNames = os.path.relpath(childrenLocations[0], manifestDir)

        self.update_column_content(file_location, SOURCE_OF_COLUMN, viewNames)

    def update_derived_from(self, file_location, mime):
        # For now each view or thumbnail file only can have one derived from file
        fileDF = self.get_file_dataframe(file_location)
        manifestDir = fileDF["manifest_dir"].iloc[0]
        parentLocation = []

        mDF = pd.read_excel(os.path.join(manifestDir, "manifest.xlsx"))
        parentMime = None
        if mime == SCAFFOLD_VIEW_MIME:
            parentMime = SCAFFOLD_META_MIME
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            parentMime = SCAFFOLD_VIEW_MIME
        parentFileNames = mDF["filename"][mDF[ADDITIONAL_TYPES_COLUMN] == parentMime].tolist()

        # Search thumbnail in dataframe with same manifest_dir as scafflod
        # If found, set it as isSourceOf
        # If not, search file 
        if parentMime == SCAFFOLD_VIEW_MIME:
            sa = ManifestDataFrame().get_scaffold_data().get_scaffold_annotations()
            for i in sa:
                if i.get_children() and file_location in i.get_children():
                    parentLocation = i.get_location()
            if parentLocation:
                parentFileNames = [os.path.relpath(parentLocation, manifestDir)]
            else:
                parentLocations = OnDiskFiles().get_scaffold_data().get_view_files()
                parentFileNames = [os.path.relpath(parentLocation, manifestDir) for parentLocation in parentLocations]

        if not parentFileNames:
            # Search from files
            parentLocations = []
            if parentMime == SCAFFOLD_VIEW_MIME:
                parentLocations = OnDiskFiles().get_scaffold_data().get_view_files()
            elif parentMime == SCAFFOLD_META_MIME:
                parentLocations = OnDiskFiles().get_scaffold_data().get_metadata_files()
            parentFileNames = [os.path.relpath(parentLocation, manifestDir) for parentLocation in parentLocations]

        self.update_column_content(file_location, DERIVED_FROM_COLUMN, parentFileNames[0])

    def update_additional_type(self, file_location, file_mime):
        self.update_column_content(file_location, ADDITIONAL_TYPES_COLUMN, file_mime)

    def update_supplemental_json(self, file_location, annotation_data):
        self.update_column_content(file_location, SUPPLEMENTAL_JSON_COLUMN, annotation_data)

    def update_anatomical_entity(self, file_location, annotation_data):
        self.update_column_content(file_location, ANATOMICAL_ENTITY_COLUMN, annotation_data)

    def update_column_content(self, file_location, column_name, content):
        # Update the cells with row: file_location, column: column_name to content
        fileDF = self.get_file_dataframe(file_location)
        for index, row in fileDF.iterrows():
            mDF = pd.read_excel(os.path.join(row["manifest_dir"], "manifest.xlsx"), sheet_name=row["sheet_name"])
            if column_name not in mDF.columns:
                mDF[column_name] = ""

            mDF.loc[mDF["filename"] == row['filename'], column_name] = content
            mDF.to_excel(os.path.join(row["manifest_dir"], "manifest.xlsx"), sheet_name=row["sheet_name"], index=False, header=True)

    class Scaffold(object):
        _data = {
            'annotations': [],
            'locations': [],
        }

        def __init__(self, parent):
            self._parent = parent

        def set_scaffold_annotations(self, annotations):
            self._data['annotations'] = annotations

        def get_scaffold_annotations(self):
            return self._data['annotations']

        def set_scaffold_locations(self, locations):
            self._data['locations'] = locations

        def get_scaffold_locations(self):
            return self._data['locations']

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
                manifest_view_derived_from = self._parent.get_matching_entry(FILE_LOCATION_COLUMN, i, DERIVED_FROM_COLUMN)
                manifest_view_derived_from_files = []
                for j in manifest_view_derived_from:
                    derived_from_files = self._parent.get_matching_entry(FILENAME_COLUMN, j, FILE_LOCATION_COLUMN)
                    manifest_view_derived_from_files.extend(derived_from_files)

                if len(manifest_view_derived_from_files) == 1:
                    if i in on_disk_files and manifest_view_derived_from_files[0] not in on_disk_parent_files:
                        errors.append(IncorrectDerivedFromError(i, incorrect_mime))

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
                        errors.append(IncorrectSourceOfError(i, incorrect_mime))
                    elif len(manifest_source_of) == 1:
                        source_of_files_list = []
                        source_ofs = manifest_source_of[0].split("\n")
                        for source_of in source_ofs:
                            source_of_files = self._parent.get_matching_entry(FILENAME_COLUMN, source_of, FILE_LOCATION_COLUMN)
                            source_of_files_list.extend(source_of_files)

                        if not all([item in on_disk_child_files for item in source_of_files_list]):
                            errors.append(IncorrectSourceOfError(i, incorrect_mime))

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

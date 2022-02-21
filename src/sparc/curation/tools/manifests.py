import os
from pathlib import Path

import pandas as pd
from sparc.curation.tools.annotations.scaffold import ScaffoldAnnotation
from sparc.curation.tools.errors import IncorrectAnnotationError, NotAnnotatedError, IncorrectDerivedFromError, \
    IncorrectSourceOfError

from sparc.curation.tools.base import Singleton
from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, FILENAME_COLUMN, SUPPLEMENTAL_JSON_COLUMN, \
    ADDITIONAL_TYPES_COLUMN, ANATOMICAL_ENTITY_COLUMN, SCAFFOLD_FILE_MIME, SCAFFOLD_VIEW_MIME, \
        SCAFFOLD_THUMBNAIL_MIME, SCAFFOLD_DIR_MIME, CONTEXT_INFO_MIME

from sparc.curation.tools.utilities import convert_to_bytes, is_same_file

class ManifestDataFrame(metaclass=Singleton):
    # dataFrame_dir = ""
    _manifestDataFrame = None
    _scaffold_data = None
    _dataset_dir = None

    def setup_dataframe(self, dataset_dir):
        self._dataset_dir = dataset_dir
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
        """
        " If there isn't any manifest file under dataset dir, create one
        """
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

    def get_dataset_dir(self):
        return self._dataset_dir

    def get_file_dataframe(self, file_location):
        """
        " Get file dataframe which match the file_location
        """
        manifestDataFrame = self._manifestDataFrame
        fileDir = os.path.dirname(file_location)
        fileName = os.path.basename(file_location)
        # Search data rows belong to the same file by file_location
        same_file = []
        for index, row in manifestDataFrame.iterrows():
            location = os.path.join(row["manifest_dir"], row["filename"])
            same_file.append(is_same_file(file_location, location))
        fileDF = manifestDataFrame[same_file]

        # If fileDF is empty, means there's no manifest file contain this file's annotation.
        if fileDF.empty:
            newRow = pd.DataFrame({"filename": fileName}, index=[1])
            # Check if there's manifest file under same Scaffold File Dir. If yes get data from it.
            # If no manifest file create new manifest file. Add file to the manifest.
            if not manifestDataFrame[manifestDataFrame["manifest_dir"] == fileDir].empty:
                mDF = pd.read_excel(os.path.join(fileDir, "manifest.xlsx"))
                newRow = mDF.append(newRow, ignore_index=True)
            newRow.to_excel(os.path.join(fileDir, "manifest.xlsx"), index=False, header=True)
        return fileDF

    def update_source_of_column(self, file_location, mime):
        fileDF = self.get_file_dataframe(file_location)
        manifestDir = fileDF["manifest_dir"].iloc[0]

        mDF = pd.read_excel(os.path.join(manifestDir, "manifest.xlsx"))
        if SOURCE_OF_COLUMN not in mDF.columns:
            mDF[SOURCE_OF_COLUMN] = ""

        childrenLocations = []
        if mime == SCAFFOLD_FILE_MIME:
            childrenLocations = OnDiskFiles().get_scaffold_data().get_metadata_children_files()[file_location]
            viewNames = [os.path.relpath(children, manifestDir) for children in childrenLocations]
            mDF.loc[mDF["filename"].str.contains(r'\(/|\)*' + fileName), SOURCE_OF_COLUMN] = ','.join(viewNames)
        
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
            if not childrenLocations:
                childrenLocations = OnDiskFiles().get_scaffold_data().get_thumbnail_files()
            # viewNames = [os.path.relpath(children, manifestDir) for children in childrenLocations]
                viewNames = os.path.relpath(childrenLocations[0], manifestDir)
            mDF.loc[mDF["filename"].str.contains(r'\(/|\)*' + fileName), SOURCE_OF_COLUMN] = viewNames

        mDF.to_excel(os.path.join(manifestDir, "manifest.xlsx"), index=False, header=True)

    def update_derived_from(self, file_location, mime):
        # For now each view or thumbnail file only can have one derived from file
        fileDF = self.get_file_dataframe(file_location)
        manifestDir = fileDF["manifest_dir"].iloc[0]
        parentLocation = []

        mDF = pd.read_excel(os.path.join(manifestDir, "manifest.xlsx"))
        parentMime = None
        if mime == SCAFFOLD_VIEW_MIME:
            parentMime = SCAFFOLD_FILE_MIME
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
            if not parentLocation:
                parentLocations = OnDiskFiles().get_scaffold_data().get_view_files()
                parentFileNames = [os.path.relpath(parentLocation, manifestDir) for parentLocation in parentLocations]

        if not parentFileNames:
            # Search from files
            parentLocations = []
            if parentMime == SCAFFOLD_VIEW_MIME:
                parentLocations = OnDiskFiles().get_scaffold_data().get_view_files()
            elif parentMime == SCAFFOLD_FILE_MIME:
                parentLocations = OnDiskFiles().get_scaffold_data().get_metadata_files()
            parentFileNames = [os.path.relpath(parentLocation, manifestDir) for parentLocation in parentLocations]

        self.update_column_content(file_location, DERIVED_FROM_COLUMN, parentFileNames[0])

    def update_additional_type(self, file_location, file_mime):
        self.update_column_content(file_location,ADDITIONAL_TYPES_COLUMN, file_mime)

    def update_supplemental_json(self, file_location, annotation_data):
        self.update_column_content(file_location,SUPPLEMENTAL_JSON_COLUMN, annotation_data)

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
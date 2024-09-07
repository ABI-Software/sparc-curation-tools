import os
import pathlib
from pathlib import Path
import pandas as pd

from sparc.curation.tools.errors import BadManifestError, AnnotationDirectoryNoWriteAccess
from sparc.curation.tools.helpers.base import Singleton
from sparc.curation.tools.definitions import (
    FILE_LOCATION_COLUMN, FILENAME_COLUMN, SUPPLEMENTAL_JSON_COLUMN,
    ADDITIONAL_TYPES_COLUMN, ANATOMICAL_ENTITY_COLUMN,
    SCAFFOLD_META_MIME, SCAFFOLD_THUMBNAIL_MIME,
    PLOT_CSV_MIME, PLOT_TSV_MIME, DERIVED_FROM_COLUMN,
    SOURCE_OF_COLUMN, MANIFEST_DIR_COLUMN, MANIFEST_FILENAME, SHEET_NAME_COLUMN
)
from sparc.curation.tools.utilities import is_same_file


class ManifestDataFrame(metaclass=Singleton):
    """
    A singleton class for managing manifest data frames.

    This class provides methods to manipulate and access data in the manifest data frame.
    """

    _manifestDataFrame = None
    _dataset_dir = None

    def setup_dataframe(self, dataset_dir):
        """
        Set up the manifest data frame.

        Args:
            dataset_dir (str): The directory containing the dataset.

        Returns:
            ManifestDataFrame: The instance of the ManifestDataFrame class.
        """
        self._dataset_dir = dataset_dir
        self._read_manifests()
        return self

    def _read_manifests(self, depth=0):
        """
        Recursively read the manifest files in the dataset directory.

        Args:
            depth (int): The current depth of recursive manifest reading.

        Raises:
            BadManifestError: If a manifest sanitization error is found.
        """
        self._manifestDataFrame = pd.DataFrame()
        for r in Path(self._dataset_dir).rglob(MANIFEST_FILENAME):
            with pd.ExcelFile(r) as xl_file:
                for sheet_name in xl_file.sheet_names:
                    currentDataFrame = pd.read_excel(xl_file, sheet_name=sheet_name, dtype=str)
                    currentDataFrame[SHEET_NAME_COLUMN] = sheet_name
                    currentDataFrame[MANIFEST_DIR_COLUMN] = os.path.dirname(r)
                    self._manifestDataFrame = pd.concat([currentDataFrame, self._manifestDataFrame])

        if not self._manifestDataFrame.empty:
            self._manifestDataFrame[FILE_LOCATION_COLUMN] = self._manifestDataFrame.apply(
                lambda row: os.path.join(row[MANIFEST_DIR_COLUMN], row[FILENAME_COLUMN]) if pd.notnull(
                    row[FILENAME_COLUMN]) else None, axis=1)

        sanitised = self._sanitise_dataframe()
        if sanitised and depth == 0:
            self._read_manifests(depth + 1)
        elif sanitised and depth > 0:
            raise BadManifestError('Manifest sanitization error found.')

    def create_manifest(self, manifest_dir):
        """
        Create a new manifest file.

        Args:
            manifest_dir (str): The directory for the new manifest file.
        """
        self._manifestDataFrame[FILENAME_COLUMN] = ''
        self._manifestDataFrame[FILE_LOCATION_COLUMN] = ''
        self._manifestDataFrame[MANIFEST_DIR_COLUMN] = manifest_dir

    def is_defined(self):
        return self._manifestDataFrame is not None

    def is_empty(self):
        return self._manifestDataFrame.empty

    def check_directory_write_permission(self, directory_path):
        """
        Checks the write permission for a given directory and raises an exception if it is not writable.

        Args:
            directory_path (str): The directory path to check for write permission.

        Raises:
            AnnotationDirectoryNoWriteAccess: If the specified directory is not writable.

        Returns:
            None
        """
        # List to keep track of checked directories to avoid duplicate checks
        checked_directories = []

        if self._manifestDataFrame.empty:
            # If the manifest is empty, create a new one at the given directory path
            ManifestDataFrame().create_manifest(directory_path)
        else:
            for manifest_dir in self._manifestDataFrame[MANIFEST_DIR_COLUMN]:
                if manifest_dir not in checked_directories:
                    checked_directories.append(manifest_dir)  # Add the directory to the checked directories list
                    if not os.access(manifest_dir, os.W_OK):  # Check if the directory is writable
                        raise AnnotationDirectoryNoWriteAccess(f"Cannot write to directory {manifest_dir}.")

    def _sanitise_column_heading(self, column_names, sanitised_heading):
        """
        Sanitize the column names related to 'derived from'.

        Args:
            column_names (list): List of column names.
        """
        sanitised = False
        bad_column_name = ''
        for column_name in column_names:
            if column_name.lower() == sanitised_heading.lower():
                if column_name != sanitised_heading:
                    bad_column_name = column_name
                break

        if bad_column_name:
            manifests = [row[MANIFEST_DIR_COLUMN] for i, row in
                         self._manifestDataFrame[self._manifestDataFrame[bad_column_name].notnull()].iterrows()]
            unique_manifests = list(set(manifests))
            for manifest_dir in unique_manifests:
                current_manifest = os.path.realpath(os.path.join(manifest_dir, MANIFEST_FILENAME))
                mDF = pd.read_excel(current_manifest, dtype=str)
                mDF.rename(columns={bad_column_name: sanitised_heading}, inplace=True)
                mDF.to_excel(current_manifest, index=False, header=True)
                sanitised = True

            if not unique_manifests:
                manifests_to_sanitise = []
                for manifest_dir in self._manifestDataFrame[MANIFEST_DIR_COLUMN]:
                    current_manifest = os.path.realpath(os.path.join(manifest_dir, MANIFEST_FILENAME))
                    if current_manifest not in manifests_to_sanitise:
                        manifests_to_sanitise.append(current_manifest)

                for manifest in manifests_to_sanitise:
                    mDF = pd.read_excel(manifest, dtype=str)
                    mDF.drop(columns=[bad_column_name], inplace=True)
                    mDF.to_excel(manifest, index=False, header=True)

                self._manifestDataFrame.drop(columns=[bad_column_name])
                sanitised = True

        return sanitised

    def _sanitise_dataframe(self):
        column_names = self._manifestDataFrame.columns
        sanitised = self._sanitise_column_heading(column_names, DERIVED_FROM_COLUMN)
        sanitised = self._sanitise_column_heading(column_names, SOURCE_OF_COLUMN) or sanitised
        sanitised = self._sanitise_column_heading(column_names, ANATOMICAL_ENTITY_COLUMN) or sanitised
        return sanitised

    # region -----Get-----
    def _get_matching_dataframe(self, file_location):
        same_file = []

        for index, row in self._manifestDataFrame.iterrows():
            location = os.path.join(row[MANIFEST_DIR_COLUMN], row[FILENAME_COLUMN])
            same_file.append(is_same_file(file_location, location))

        return self._manifestDataFrame[same_file]

    def get_matching_entry(self, column_heading, value, out_column_heading=FILENAME_COLUMN):
        """
        Get a list of entries from the specified column based on a matching condition.

        Args:
            column_heading (str): The column to filter based on the 'value'.
            value: The value to match in the specified 'column_heading'.
            out_column_heading (str): The column from which to retrieve matching entries.

        Returns:
            list: A list of matching entries from the 'out_column_heading' column.
        """
        matching_files = []

        # Check if the specified columns exist in the manifest DataFrame
        if column_heading in self._manifestDataFrame.columns and out_column_heading in self._manifestDataFrame.columns:
            condition = self._manifestDataFrame[column_heading] == value
            matching_files = list(self._manifestDataFrame[out_column_heading][condition])
        return matching_files

    def get_entry_that_includes(self, column_heading, value, out_column_heading=FILENAME_COLUMN):
        """
        Get a list of entries from the specified column based on partial matching condition.

        Args:
            column_heading (str): The column to search for partial matches.
            value (str): The value to search for within the specified 'column_heading'.
            out_column_heading (str): The column from which to retrieve matching entries.

        Returns:
            list: A list of matching entries from the 'out_column_heading' column.
        """
        matching_files = []

        # Check if the specified columns exist in the manifest DataFrame
        if column_heading in self._manifestDataFrame.columns and out_column_heading in self._manifestDataFrame.columns:
            condition = self._manifestDataFrame[column_heading].str.contains(value, na=False, regex=False)
            matching_files = list(self._manifestDataFrame[out_column_heading][condition])
        return matching_files

    def get_filepath_on_disk(self, file_location):
        filenames = self.get_matching_entry(FILENAME_COLUMN, file_location, FILE_LOCATION_COLUMN)
        return filenames[0]

    def scaffold_get_metadata_files(self):
        return self.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_META_MIME, FILE_LOCATION_COLUMN)

    def scaffold_get_plot_files(self):
        return self.get_matching_entry(ADDITIONAL_TYPES_COLUMN, PLOT_CSV_MIME, FILE_LOCATION_COLUMN) + \
            self.get_matching_entry(ADDITIONAL_TYPES_COLUMN, PLOT_TSV_MIME, FILE_LOCATION_COLUMN)

    def get_manifest_directory(self, file_location):
        return self.get_matching_entry(FILE_LOCATION_COLUMN, file_location, MANIFEST_DIR_COLUMN)

    def get_derived_from(self, file_location):
        return self.get_matching_entry(FILE_LOCATION_COLUMN, file_location, DERIVED_FROM_COLUMN)

    def get_source_of(self, file_location):
        return self.get_entry_that_includes(FILE_LOCATION_COLUMN, file_location, SOURCE_OF_COLUMN)

    def get_filename(self, file_location):
        return self.get_entry_that_includes(FILE_LOCATION_COLUMN, file_location, FILENAME_COLUMN)

    def get_file_dataframe(self, file_location, manifest_dir=None):
        """
        Get file dataframe which match the file_location
        """
        manifestDataFrame = self._manifestDataFrame
        if manifest_dir:
            file_name = pathlib.PureWindowsPath(os.path.relpath(file_location, manifest_dir)).as_posix()
        else:
            manifest_dir = os.path.dirname(file_location)
            if manifestDataFrame.empty:
                self.create_manifest(manifest_dir)

            file_name = os.path.basename(file_location)

        # Search data rows to find match to the same file by file_location.
        fileDF = self._get_matching_dataframe(file_location)

        # If fileDF is empty, means there's no manifest file containing this file's annotation.
        if fileDF.empty:
            newRow = pd.DataFrame({FILENAME_COLUMN: file_name}, index=[1])
            # Check if there's manifest file under same Scaffold File Dir. If yes get data from it.
            # If no manifest file create new manifest file. Add file to the manifest.
            if not manifestDataFrame[manifestDataFrame[MANIFEST_DIR_COLUMN] == manifest_dir].empty:
                mDF = pd.read_excel(os.path.join(manifest_dir, MANIFEST_FILENAME), dtype=str)
                newRow = pd.concat([mDF, newRow], ignore_index=True)

            manifest_absolute_path = os.path.realpath(os.path.join(manifest_dir, MANIFEST_FILENAME))
            newRow.to_excel(manifest_absolute_path, index=False, header=True)

            # Re-read manifests to find dataframe for newly added entry.
            self._read_manifests()
            fileDF = self._get_matching_dataframe(file_location)
            # fileDF = newRow
        return fileDF

    # endregion

    # region -----Update-----
    def update_plot_annotation(self, file_location, supplemental_json_data, thumbnail_location):
        if file_location.endswith(".csv"):
            self.update_additional_type(file_location, PLOT_CSV_MIME)
        elif file_location.endswith(".tsv") or file_location.endswith(".txt"):
            self.update_additional_type(file_location, PLOT_TSV_MIME)
        self.update_supplemental_json(file_location, supplemental_json_data)

        # Annotate thumbnail file
        if thumbnail_location:
            self.update_additional_type(thumbnail_location, SCAFFOLD_THUMBNAIL_MIME)
            self.update_column_content(thumbnail_location, DERIVED_FROM_COLUMN, file_location)
            self.update_column_content(file_location, SOURCE_OF_COLUMN, thumbnail_location)

    def update_additional_type(self, file_location, file_mime):
        self.update_column_content(file_location, ADDITIONAL_TYPES_COLUMN, file_mime)

    def update_supplemental_json(self, file_location, annotation_data):
        self.update_column_content(file_location, SUPPLEMENTAL_JSON_COLUMN, annotation_data)

    def update_anatomical_entity(self, file_location, annotation_data):
        """
        Update the anatomical entity information in the manifest for a given file.

        Args:
            file_location (str): The file location.
            annotation_data (str): The anatomical entity annotation data.
        """
        self.update_column_content(file_location, ANATOMICAL_ENTITY_COLUMN, annotation_data)

    def update_column_content(self, file_location, column_name, content, append=False):
        """
        Update the content of a specified column for a given file location.

        Args:
            file_location (str): The file location.
            column_name (str): The name of the column to update.
            content (str): The content to update in the column.
            append (bool): Whether to append the content if the column already contains data.

        Raises:
            FileNotFoundError: If the file is not found in the manifest.
        """
        # Update the cells with row: file_location, column: column_name to content
        fileDF = self.get_file_dataframe(file_location)
        for index, row in fileDF.iterrows():
            mDF = pd.read_excel(os.path.join(row[MANIFEST_DIR_COLUMN], MANIFEST_FILENAME),
                                sheet_name=row[SHEET_NAME_COLUMN], dtype=str)

            if content and os.path.isabs(content):
                content = pathlib.PureWindowsPath(os.path.relpath(content, row[MANIFEST_DIR_COLUMN])).as_posix()
            if column_name not in mDF.columns:
                mDF[column_name] = ""

            if append:
                mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name] \
                    = mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name].fillna(content)

                def _append_new_line_separated(x):
                    if x:
                        val = x + "\n" + content if content not in x.split("\n") else x
                    else:
                        val = content

                    return val

                result = mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name].apply(_append_new_line_separated)
                mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name] = result
            else:
                if content is None:
                    content = ""
                mDF.loc[mDF[FILENAME_COLUMN] == row[FILENAME_COLUMN], column_name] = content

            manifest_absolute_path = os.path.realpath(os.path.join(row[MANIFEST_DIR_COLUMN], MANIFEST_FILENAME))
            mDF.to_excel(manifest_absolute_path, sheet_name=row[SHEET_NAME_COLUMN],
                         index=False, header=True)

        self._read_manifests()

    # endregion

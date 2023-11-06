import os.path

import pandas as pd

from sparc.curation.tools.helpers.base import Singleton
from sparc.curation.tools.errors import IncorrectAnnotationError, NotAnnotatedError, IncorrectDerivedFromError, \
    IncorrectSourceOfError, OldAnnotationError
from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN, FILENAME_COLUMN, ADDITIONAL_TYPES_COLUMN, \
    SCAFFOLD_META_MIME, SCAFFOLD_VIEW_MIME, \
    SCAFFOLD_THUMBNAIL_MIME, DERIVED_FROM_COLUMN, SOURCE_OF_COLUMN, MANIFEST_DIR_COLUMN, \
    OLD_SCAFFOLD_MIMES, MIMETYPE_TO_PARENT_FILETYPE_MAP, MIMETYPE_TO_FILETYPE_MAP
from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame


class ErrorManager(metaclass=Singleton):
    """
    Class to check and manage the different or errors between the annotations in the manifest dataframe and
    the actual files on disk.
    """

    def __init__(self):
        self.on_disk = OnDiskFiles()
        self.manifest = ManifestDataFrame()
        self.on_disk_metadata_files = None
        self.on_disk_view_files = None
        self.on_disk_thumbnail_files = None
        self.manifest_metadata_files = None
        self.manifest_view_files = None
        self.manifest_thumbnail_files = None
        self.on_disk_context_info_files = None

        self.update_content()

    def update_content(self):
        """
        Update the content of the on-disk and manifest files.
        """
        self.on_disk_metadata_files = self.on_disk.get_metadata_files()
        self.on_disk_view_files = self.on_disk.get_view_files()
        self.on_disk_thumbnail_files = self.on_disk.get_thumbnail_files()
        self.on_disk_plot_thumbnail_files = self.on_disk.get_plot_thumbnails()
        self.on_disk_context_info_files = self.on_disk.get_context_info_files()

        self.manifest_metadata_files = self.manifest.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_META_MIME,
                                                                        FILE_LOCATION_COLUMN)
        self.manifest_view_files = self.manifest.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_VIEW_MIME,
                                                                    FILE_LOCATION_COLUMN)
        self.manifest_thumbnail_files = self.manifest.get_matching_entry(ADDITIONAL_TYPES_COLUMN,
                                                                         SCAFFOLD_THUMBNAIL_MIME,
                                                                         FILE_LOCATION_COLUMN)

    # === Find Errors ===

    def get_old_annotations(self):
        """
        Get errors for old annotations in the manifest dataframe.

        Returns:
            list: List of OldAnnotationError objects.
        """
        errors = []
        OLD_ANNOTATIONS = OLD_SCAFFOLD_MIMES

        for old_annotation in OLD_ANNOTATIONS:
            old_manifest_metadata_files = self.manifest.get_matching_entry(ADDITIONAL_TYPES_COLUMN, old_annotation,
                                                                           FILE_LOCATION_COLUMN)
            for i in old_manifest_metadata_files:
                errors.append(OldAnnotationError(i, old_annotation))

        return errors

    def get_missing_annotations(self):
        """
        Get errors for missing annotations in the manifest dataframe.

        Returns:
            list: List of NotAnnotatedError objects.
        """
        errors = []

        for i in self.on_disk_metadata_files:
            if i not in self.manifest_metadata_files:
                errors.append(NotAnnotatedError(i, SCAFFOLD_META_MIME))

        for i in self.on_disk_view_files:
            if i not in self.manifest_view_files:
                errors.append(NotAnnotatedError(i, SCAFFOLD_VIEW_MIME))

        # Derive thumbnail files from view files, now we don't consider all image files to be annotation errors.
        # manifest_thumbnail_files = manifest.get_matching_entry(ADDITIONAL_TYPES_COLUMN, SCAFFOLD_THUMBNAIL_MIME, FILE_LOCATION_COLUMN)
        # for i in on_disk_thumbnail_files:
        #     if i not in manifest_thumbnail_files:
        #         errors.append(NotAnnotatedError(i, SCAFFOLD_THUMBNAIL_MIME))

        return errors

    def get_incorrect_annotations(self):
        """
        Get errors for incorrect annotations in the manifest dataframe.

        Returns:
            list: List of IncorrectAnnotationError objects.
        """
        errors = []

        for i in self.manifest_metadata_files:
            if i not in self.on_disk_metadata_files:
                errors.append(IncorrectAnnotationError(i, SCAFFOLD_META_MIME))

        for i in self.manifest_view_files:
            if i not in self.on_disk_view_files:
                errors.append(IncorrectAnnotationError(i, SCAFFOLD_VIEW_MIME))

        for i in self.manifest_thumbnail_files:
            if i not in self.on_disk_thumbnail_files and i not in self.on_disk_plot_thumbnail_files:
                errors.append(IncorrectAnnotationError(i, SCAFFOLD_THUMBNAIL_MIME))

        return errors

    def _process_incorrect_derived_from(self, on_disk_files, on_disk_parent_files, manifest_files, incorrect_mime):
        """
        Helper method to process incorrect derived from errors.

        Args:
            on_disk_files (list): List of on-disk files.
            on_disk_parent_files (list): List of parent files on disk.
            manifest_files (list): List of files annotated in manifest data frame.
            incorrect_mime (str): Incorrect MIME type.

        Returns:
            list: List of IncorrectDerivedFromError objects.
        """
        errors = []

        for i in manifest_files:
            manifest_derived_from = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, i, DERIVED_FROM_COLUMN)
            manifest_derived_from_files = []
            for j in manifest_derived_from:
                derived_from_files = self.manifest.get_matching_entry(FILENAME_COLUMN, j, FILE_LOCATION_COLUMN)
                manifest_derived_from_files.extend(derived_from_files)

            if len(manifest_derived_from_files) == 0:
                errors.append(IncorrectDerivedFromError(i, incorrect_mime, on_disk_parent_files))
            elif len(manifest_derived_from_files) == 1:
                if i in on_disk_files and manifest_derived_from_files[0] not in on_disk_parent_files:
                    errors.append(IncorrectDerivedFromError(i, incorrect_mime, on_disk_parent_files))

        return errors

    def get_incorrect_derived_from(self):
        """
        Get errors for incorrect derived from relationships in the manifest dataframe.

        Returns:
            list: List of IncorrectDerivedFromError objects.
        """
        errors = []

        view_derived_from_errors = self._process_incorrect_derived_from(self.on_disk_view_files,
                                                                        self.on_disk_metadata_files,
                                                                        self.manifest_view_files, SCAFFOLD_VIEW_MIME)
        errors.extend(view_derived_from_errors)

        thumbnail_derived_from_errors = self._process_incorrect_derived_from(
            self.on_disk_thumbnail_files, self.on_disk_view_files, self.manifest_thumbnail_files,
            SCAFFOLD_THUMBNAIL_MIME)
        errors.extend(thumbnail_derived_from_errors)

        return errors

    def _process_incorrect_source_of(self, on_disk_files, mimetype, on_disk_child_files):
        """
        Helper method to process incorrect source of errors.

        Args:
            on_disk_files (list): List of on-disk files.
            mimetype (str): MIME type of source file type.
            on_disk_child_files (list): List of child files on disk.

        Returns:
            list: List of IncorrectSourceOfError objects.
        """
        errors = []
        for on_disk_file in on_disk_files:
            source_ofs = self.manifest.get_source_of(on_disk_file)
            for source_of_entry in source_ofs:
                if not pd.isna(source_of_entry):
                    source_of_entries = source_of_entry.split('\n')
                    for source_of in source_of_entries:
                        source_of_mimetype = self.manifest.get_matching_entry(FILENAME_COLUMN, source_of, ADDITIONAL_TYPES_COLUMN)
                        if _is_valid_mimetype_for(mimetype, source_of_mimetype[0]):
                            on_disk_source_of = self.manifest.get_matching_entry(FILENAME_COLUMN, source_of, FILE_LOCATION_COLUMN)
                            if not os.path.isfile(on_disk_source_of[0]):
                                errors.append(IncorrectSourceOfError(on_disk_file, mimetype, on_disk_child_files))
                        else:
                            corrected_source_of_entries = source_of_entries[:] + on_disk_child_files
                            corrected_source_of_entries.remove(source_of)
                            errors.append(IncorrectSourceOfError(on_disk_file, mimetype, corrected_source_of_entries))
                else:
                    errors.append(IncorrectSourceOfError(on_disk_file, mimetype, on_disk_child_files))

        if len(errors) == 0:
            for on_disk_file in on_disk_child_files:
                derived_from = self.manifest.get_derived_from(on_disk_file)
                for derived_from_entry in derived_from:
                    if not pd.isna(derived_from_entry):
                        on_disk_dervied_from = self.manifest.get_matching_entry(FILENAME_COLUMN, derived_from_entry, FILE_LOCATION_COLUMN)
                        derived_from_source_of = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, on_disk_dervied_from[0], SOURCE_OF_COLUMN)
                        derived_from_filename = self.manifest.get_filename(on_disk_file)
                        if not derived_from_source_of or derived_from_filename[0] not in derived_from_source_of[0].split('\n'):
                            errors.append(IncorrectSourceOfError(on_disk_dervied_from[0], mimetype, on_disk_child_files))


        return errors

    def get_incorrect_source_of(self):
        """
        Get errors for incorrect source of relationships in the manifest dataframe.

        Returns:
            list: List of IncorrectSourceOfError objects.
        """
        errors = []

        on_disk_source_of_files = self.on_disk_view_files + self.on_disk_context_info_files
        metadata_source_of_errors = self._process_incorrect_source_of(self.on_disk_metadata_files, SCAFFOLD_META_MIME, on_disk_source_of_files)
        errors.extend(metadata_source_of_errors)

        view_source_of_errors = self._process_incorrect_source_of(self.on_disk_view_files, SCAFFOLD_VIEW_MIME, self.on_disk_thumbnail_files)
        errors.extend(view_source_of_errors)

        return errors

    def get_incorrect_complementary(self):
        """
        Get errors for incorrect complementary files in the manifest dataframe.

        Returns:
            list: List of errors.
        """
        errors = []

        incorrect_derived_from_errors = []
        for i in self.manifest_view_files:
            manifest_source_of = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, i, SOURCE_OF_COLUMN)

            if pd.isna(manifest_source_of).any() or len(manifest_source_of) == 0:
                match_rating = [calculate_match(tt, i) for tt in self.on_disk_thumbnail_files]
                max_value = max(match_rating)
                max_index = match_rating.index(max_value)
                errors.append(NotAnnotatedError(self.on_disk_thumbnail_files[max_index], SCAFFOLD_THUMBNAIL_MIME))
            else:
                source_of_files_list = []
                source_ofs = manifest_source_of[0].split("\n")
                for source_of in source_ofs:
                    source_of_files = self.manifest.get_matching_entry(FILENAME_COLUMN, source_of, FILE_LOCATION_COLUMN)
                    source_of_files_list.extend(source_of_files)

                manifest_filename = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, i, FILENAME_COLUMN)
                for source_of in source_of_files_list:
                    values = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, source_of, DERIVED_FROM_COLUMN)
                    mimetypes = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, source_of,
                                                                 ADDITIONAL_TYPES_COLUMN)
                    if mimetypes[0] != SCAFFOLD_THUMBNAIL_MIME:
                        errors.append(NotAnnotatedError(source_of, SCAFFOLD_THUMBNAIL_MIME))

                    if not values[0]:
                        incorrect_derived_from_errors.append(
                            IncorrectDerivedFromError(source_of, SCAFFOLD_THUMBNAIL_MIME, manifest_filename))

        errors.extend(incorrect_derived_from_errors)
        return errors

    # === Fix Errors ===

    def update_derived_from(self, file_location, mime, target):
        """
        Update the 'Derived From' column in the manifest data frame for the given file location.
    
        Args:
            file_location (str): The file location to update.
            mime (str): The MIME type of the file.
            target (list): List of target file locations.
    
        """
        # Get the source manifest entry for the given file location
        source_manifest = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, file_location, MANIFEST_DIR_COLUMN)

        # List to store target filenames
        target_filenames = []

        if mime == SCAFFOLD_VIEW_MIME:
            # If the MIME type is SCAFFOLD_VIEW_MIME, find the matching target filenames
            for t in target:
                target_manifest = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                if source_manifest == target_manifest:
                    target_filenames.extend(
                        self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN))

        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            # If the MIME type is SCAFFOLD_THUMBNAIL_MIME, find the best matching target filename
            source_filenames = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, file_location, FILENAME_COLUMN)
            source_filename = source_filenames[0]
            best_match = -1
            for t in target:
                target_manifest = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                if source_manifest == target_manifest:
                    matching_entries = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN)
                    match_rating = [calculate_match(tt, source_filename) for tt in matching_entries]
                    max_value = max(match_rating)
                    max_index = match_rating.index(max_value)
                    if max_value > best_match:
                        best_match = max_value
                        target_filenames = [matching_entries[max_index]]

        # Update the 'Derived From' column content with the target filenames
        self.manifest.update_column_content(file_location, DERIVED_FROM_COLUMN, "\n".join(target_filenames))

    def update_source_of(self, file_location, mime, target):
        """
        Update the 'Source Of' column in the manifest data frame for the given file location.
    
        Args:
            file_location (str): The file location to update.
            mime (str): The MIME type of the file.
            target (list): List of target file locations.
    
        """
        # Get the source manifest entry for the given file location
        source_manifest = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, file_location, MANIFEST_DIR_COLUMN)

        # List to store target filenames
        target_filenames = []

        if mime == SCAFFOLD_META_MIME:
            # If the MIME type is SCAFFOLD_META_MIME, find the matching target filenames
            for t in target:
                target_manifest = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                if source_manifest == target_manifest:
                    target_filenames.extend(
                        self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN))

        elif mime == SCAFFOLD_VIEW_MIME:
            # If the MIME type is SCAFFOLD_VIEW_MIME, find the best matching target filename
            source_filenames = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, file_location, FILENAME_COLUMN)
            source_filename = source_filenames[0]
            best_match = -1
            for t in target:
                target_manifest = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, MANIFEST_DIR_COLUMN)
                if source_manifest == target_manifest:
                    matching_entries = self.manifest.get_matching_entry(FILE_LOCATION_COLUMN, t, FILENAME_COLUMN)
                    match_rating = [calculate_match(tt, source_filename) for tt in matching_entries]
                    max_value = max(match_rating)
                    max_index = match_rating.index(max_value)
                    if max_value > best_match:
                        best_match = max_value
                        target_filenames = [matching_entries[max_index]]

        # Update the 'Source Of' column content with the target filenames
        self.manifest.update_column_content(file_location, SOURCE_OF_COLUMN, "\n".join(target_filenames))

    def fix_error(self, error):
        # Check files write permission
        ManifestDataFrame().check_directory_write_permission(error.get_location())

        # Correct old annotation first, then incorrect annotation, and lastly no annotation.
        if isinstance(error, OldAnnotationError) or isinstance(error, IncorrectAnnotationError):
            ManifestDataFrame().update_additional_type(error.get_location(), None)
        elif isinstance(error, NotAnnotatedError):
            ManifestDataFrame().update_additional_type(error.get_location(), error.get_mime())
        elif isinstance(error, IncorrectDerivedFromError):
            ErrorManager().update_derived_from(error.get_location(), error.get_mime(), error.get_target())
        elif isinstance(error, IncorrectSourceOfError):
            ErrorManager().update_source_of(error.get_location(), error.get_mime(), error.get_target())


def calculate_match(item1, item2):
    """
    Calculate the match rating between two items.

    Args:
        item1 (str): First item.
        item2 (str): Second item.

    Returns:
        int: Match rating.
    """
    common_prefix = ''

    for x, y in zip(item1, item2):
        if x == y:
            common_prefix += x
        else:
            break

    # Return the match rating as an integer.
    return len(common_prefix)


def _is_valid_mimetype_for(target_mimetype, source_mimetype):
    if MIMETYPE_TO_FILETYPE_MAP.get(target_mimetype, 'unknown') == MIMETYPE_TO_PARENT_FILETYPE_MAP.get(source_mimetype, 'not-found'):
        return True

    return False

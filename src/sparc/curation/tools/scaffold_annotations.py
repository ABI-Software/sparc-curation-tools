import argparse
import os

from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN
from sparc.curation.tools.helpers.error_helper import ErrorManager, fix_error
from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.utilities import convert_to_bytes


def setup_data(dataset_dir, max_size):
    """
    Sets up the dataset by retrieving data from the on-disk files and initializing the manifest dataframe.

    Args:
        dataset_dir (str): The directory path where the dataset will be set up.
        max_size (str): The maximum size that the dataset should occupy.

    Returns:
        None
    """
    OnDiskFiles().setup_dataset(dataset_dir, convert_to_bytes(max_size))
    ManifestDataFrame().setup_dataframe(dataset_dir)


# OnDisk section
def get_on_disk_metadata_files():
    return OnDiskFiles().get_metadata_files()


def get_on_disk_view_files():
    return OnDiskFiles().get_view_files()


def get_on_disk_thumbnail_files():
    return OnDiskFiles().get_thumbnail_files()


# Manifest section
def get_filename_by_location(object_text):
    ManifestDataFrame().get_matching_entry(FILE_LOCATION_COLUMN, object_text)


def update_column_content(subject_text, predicate_text, object_value, append):
    ManifestDataFrame().update_column_content(subject_text, predicate_text, object_value, append)


def _create_non_empty_list(input_list):
    output_list = []
    if isinstance(input_list, list) and len(input_list):
        if not isinstance(input_list[0], float):
            output_list = list(filter(None, input_list[0].split('\n')))

    return output_list


def get_annotated_scaffold_dictionary():
    """
    Build and return a scaffold dictionary based on scaffold annotation in manifest files.
    The annotated scaffold dictionary has the following structure:
    {
        metadata_filename: {
            view_file: [thumbnail_filename, vtk_filename, stl_filename, ...]
        }
    }

    Returns:
        dict: Scaffold dictionary.
    """
    manifest = ManifestDataFrame()
    annotated_scaffold_dictionary = {}

    # Get a list of metadata filenames in the manifest
    metadata_files = manifest.scaffold_get_metadata_files()

    for metadata_file in metadata_files:
        # Get the directory where the metadata file is located
        manifest_dir = manifest.get_manifest_directory(metadata_file)[0]

        # Get a list of view filenames associated with the metadata
        metadata_source_of = manifest.get_source_of(metadata_file)
        # Create an empty dictionary to store view and thumbnail information for this metadata
        metadata_entry = {}

        # View filenames can have multiple lines separated by a newline.
        filtered_metadata_source_of = _create_non_empty_list(metadata_source_of)

        for view in filtered_metadata_source_of:
            view_filename = os.path.join(manifest_dir, view)

            # Get a list of thumbnail filenames associated with the view
            view_source_of = manifest.get_source_of(view_filename)

            # Create a list to store thumbnail, etc. information for this view
            view_value = [os.path.join(manifest_dir, e) for e in _create_non_empty_list(view_source_of)]

            # Add the view entry to the metadata entry
            metadata_entry[view_filename] = view_value

        # Add the metadata entry to the annotated scaffold dictionary
        annotated_scaffold_dictionary[metadata_file] = metadata_entry

    return annotated_scaffold_dictionary


# Error section
def check_for_old_annotations():
    """
    Checks for old annotations in the manifest dataframe.

    Returns:
        list: A list of errors related to old annotations.
    """
    errors = []
    errors += ErrorManager().get_old_annotations()
    return errors


def check_additional_types_annotations():
    """
    Checks for errors in additional types annotations in the manifest dataframe.

    Returns:
        list: A list of errors related to additional types annotations.
    """
    errors = []
    errors += ErrorManager().get_missing_annotations()
    errors += ErrorManager().get_incorrect_annotations()
    return errors


def check_derived_from_annotations():
    """
    Checks for errors in derived from annotations in the manifest dataframe.

    Returns:
        list: A list of errors related to derived from annotations.
    """
    errors = []
    errors += ErrorManager().get_incorrect_derived_from()
    return errors


def check_source_of_annotations():
    """
    Checks for errors in source of annotations in the manifest dataframe.

    Returns:
        list: A list of errors related to source of annotations.
    """
    errors = []
    errors.extend(ErrorManager().get_incorrect_source_of())
    return errors


def check_complementary_annotations():
    """
    Checks for errors in complementary annotations in the manifest dataframe.

    Returns:
        list: A list of errors related to complementary annotations.
    """
    errors = []
    errors.extend(ErrorManager().get_incorrect_complementary())
    return errors


def get_errors():
    """
    Retrieves all the errors in the manifest dataframe.

    Returns:
        list: A list of all errors in the manifest dataframe.
    """
    errors = []
    ErrorManager().update_content()
    errors.extend(check_for_old_annotations())
    errors.extend(check_additional_types_annotations())
    errors.extend(check_complementary_annotations())
    errors.extend(check_derived_from_annotations())
    errors.extend(check_source_of_annotations())
    return errors


def get_confirmation_message(error=None):
    """
    "To fix this error, the 'additional types' of 'filename' in 'manifestFile' will be set to 'MIME'."
    "To fix this error, a manifestFile will be created under manifestDir, and will insert the filename in this manifestFile with 'additional types' MIME."

    "To fix this error, the data of filename in manifestFile will be deleted."
    # TODO or NOT TODO: return different message based on input error type
    """
    if error is None:
        return "Let this magic tool fix all errors for you?"

    return "Let this magic tool fix this error for you?"


def fix_errors(errors):
    failed = False
    index = 0
    while not failed and len(errors) > 0:
        current_error = errors[index]

        fix_error(current_error)

        new_errors = get_errors()
        old_errors = errors[:]
        errors = new_errors

        if old_errors == new_errors:
            index += 1
            if index == len(errors):
                failed = True
        else:
            index = 0

    return not failed


def main():
    parser = argparse.ArgumentParser(description='Check scaffold annotations for a SPARC dataset.')
    parser.add_argument("dataset_dir", help='directory to check.')
    parser.add_argument("-m", "--max-size", help="Set the max size for metadata file. Default is 2MiB", default='2MiB',
                        type=convert_to_bytes)
    parser.add_argument("-r", "--report", help="Report any errors that were found.", action='store_true')
    parser.add_argument("-f", "--fix", help="Fix any errors that were found.", action='store_true')

    args = parser.parse_args()
    dataset_dir = args.dataset_dir
    max_size = args.max_size

    # Step 1: Look at all the files in the dataset
    #   - Try to find files that I think are scaffold metadata files.
    #   - Try to find files that I think are scaffold view files.
    #   - Try ...
    OnDiskFiles().setup_dataset(dataset_dir, max_size)

    # Step 2: Read all the manifest files in the dataset
    #   - Get all the files annotated as scaffold metadata files.
    #   - Get all the files annotated as scaffold view files.
    #   - Get all the files annotated as scaffold view thumbnails.
    ManifestDataFrame().setup_dataframe(dataset_dir)

    # Step 3:
    #   - Compare the results from steps 1 and 2 and determine if they have any differences.
    #   - Problems I must look out for:
    #     - Entry in manifest file doesn't refer to an existing file.
    #     - Scaffold files I find in the dataset do not have a matching entry in a manifest.
    #     - All scaffold metadata files must have at least one view associated with it (and vice versa).
    #     - All scaffold view files should(must) have exactly one thumbnail associated with it (and vice versa).
    errors = get_errors()

    # Step 4:
    #   - Report a differences from step 1 and 2.
    if args.report:
        for error in errors:
            print(error.get_error_message())

    # Step 5:
    #   - Fix errors as identified by user.
    if args.fix:
        fix_errors(errors)


if __name__ == "__main__":
    main()

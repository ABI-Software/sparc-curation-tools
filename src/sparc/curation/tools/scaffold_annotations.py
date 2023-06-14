import argparse

from sparc.curation.tools.helpers.error_helper import ErrorManager
from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.utilities import convert_to_bytes


def setup_data(dataset_dir, max_size):
    """
    Sets up the dataset by retrieving data from the on-disk files and initializing the manifest dataframe.

    Args:
        dataset_dir (str): The directory path where the dataset will be set up.
        max_size (int): The maximum size (in bytes) that the dataset should occupy.

    Returns:
        None
    """
    OnDiskFiles().setup_dataset(dataset_dir, max_size)
    ManifestDataFrame().setup_dataframe(dataset_dir)


def get_scaffold_data_ondisk():
    """
    Retrieves the scaffold data from the on-disk files.

    Returns:
        OnDiskData: An instance of OnDiskData for accessing scaffold data.
    """
    return OnDiskFiles()


def get_manifest():
    return ManifestDataFrame()


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

    message = "Let this magic tool fix this error for you?"
    return message


def fix_error(error):
    ErrorManager().fix_error(error)


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

import argparse
import os

from sparc.curation.tools.definitions import MANIFEST_DIR_COLUMN
from sparc.curation.tools.errors import NotAnnotatedError, IncorrectAnnotationError, IncorrectDerivedFromError, IncorrectSourceOfError
from sparc.curation.tools.errors import AnnotationDirectoryNoWriteAccess
from sparc.curation.tools.manifests import ManifestDataFrame
from sparc.curation.tools.ondisk import OnDiskFiles
from sparc.curation.tools.utilities import convert_to_bytes


def check_additional_types_annotations():
    errors = []
    errors += ManifestDataFrame().get_scaffold_data().get_missing_annotations(OnDiskFiles())
    errors += ManifestDataFrame().get_scaffold_data().get_incorrect_annotations(OnDiskFiles())
    return errors


def check_derived_from_annotations():
    errors = []
    errors += ManifestDataFrame().get_scaffold_data().get_incorrect_derived_from(OnDiskFiles())
    return errors


def check_source_of_annotations():
    errors = []
    errors.extend(ManifestDataFrame().get_scaffold_data().get_incorrect_source_of(OnDiskFiles()))
    return errors


def get_errors():
    errors = []
    errors.extend(check_additional_types_annotations())
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
    checked_locations = []

    manifest = ManifestDataFrame().get_manifest()
    if manifest.empty:
        ManifestDataFrame().create_manifest(error.get_location())
    else:
        for manifest_dir in manifest[MANIFEST_DIR_COLUMN]:
            if manifest_dir not in checked_locations:
                checked_locations.append(manifest_dir)
                if not os.access(manifest_dir, os.W_OK):
                    raise AnnotationDirectoryNoWriteAccess(f"Cannot write to directory {manifest_dir}.")

    # Check incorrect annotation before no annotation.
    if isinstance(error, IncorrectAnnotationError):
        ManifestDataFrame().update_additional_type(error.get_location(), None)
    elif isinstance(error, NotAnnotatedError):
        ManifestDataFrame().update_additional_type(error.get_location(), error.get_mime())
    elif isinstance(error, IncorrectDerivedFromError):
        ManifestDataFrame().get_scaffold_data().update_derived_from(error.get_location(), error.get_mime(), error.get_target())
    elif isinstance(error, IncorrectSourceOfError):
        ManifestDataFrame().get_scaffold_data().update_source_of(error.get_location(), error.get_mime(), error.get_target())


def main():
    parser = argparse.ArgumentParser(description='Check scaffold annotations for a SPARC dataset.')
    parser.add_argument("dataset_dir", help='directory to check.')
    parser.add_argument("-m", "--max-size", help="Set the max size for metadata file. Default is 2MiB", default='2MiB', type=convert_to_bytes)
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
    #   - Report an differences from step 1 and 2.
    if args.report:
        for error in errors:
            print(error.get_error_message())

    # Step 5:
    #   - Fix errors as identified by user.
    if args.fix:
        for error in errors:
            fix_error(error)


if __name__ == "__main__":
    main()

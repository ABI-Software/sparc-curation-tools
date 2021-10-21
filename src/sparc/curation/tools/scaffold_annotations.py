import argparse
import os
import pandas as pd

from sparc.curation.tools.annotations.scaffold import IncorrectAnnotationError, NoViewError, NoThumbnailError, NoDerivedFromError, NotAnnotatedError
from sparc.curation.tools.definitions import ADDITIONAL_TYPES_COLUMN, SOURCE_OF_COLUMN, \
    DERIVED_FROM_COLUMN, SCAFFOLD_VIEW_MIME, SCAFFOLD_THUMBNAIL_MIME, SCAFFOLD_FILE_MIME
from sparc.curation.tools.errors import AnnotationDirectoryNoWriteAccess
from sparc.curation.tools.manifests import ManifestDataFrame
from sparc.curation.tools.ondisk import OnDiskFiles
from sparc.curation.tools.utilities import convert_to_bytes, is_same_file


def check_additional_types_annotations():
    errors = []
    errors += ManifestDataFrame().get_scaffold_data().get_missing_annotations(OnDiskFiles())
    errors += ManifestDataFrame().get_scaffold_data().get_incorrect_annotations(OnDiskFiles())
    return errors


def check_scaffold_view_annotations():
    errors = []
    errors.extend(ManifestDataFrame().get_scaffold_data().get_scaffold_no_view(OnDiskFiles()))
    errors.extend(ManifestDataFrame().get_scaffold_data().get_view_no_scaffold(OnDiskFiles()))
    return errors


def check_scaffold_thumbnail_annotations():
    errors = []
    errors.extend(ManifestDataFrame().get_scaffold_data().get_view_no_thumbnail(OnDiskFiles()))
    errors.extend(ManifestDataFrame().get_scaffold_data().get_thumbnail_no_view(OnDiskFiles()))
    return errors


def get_errors():
    errors = []
    errors.extend(check_additional_types_annotations())
    errors.extend(check_scaffold_view_annotations())
    errors.extend(check_scaffold_thumbnail_annotations())
    return errors


def get_confirmation_message(error):
    """
    "To fix this error, the 'additional types' of 'filename' in 'manifestFile' will be set to 'MIME'."
    "To fix this error, a manifestFile will be created under manifestDir, and will insert the filename in this manifestFile with 'additional types' MIME."

    "To fix this error, the data of filename in manifestFile will be deleted."
    # TODO or NOT TODO: return different message based on input error type
    """
    message = "Let this magic tool fix this error for you."
    return message


def set_source_of_column(file_location, mime):
    manifestDataFrame = ManifestDataFrame().get_manifest()
    # fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    # Before add view, the scaffold metadata must already been annotated in manifest, otherwise fix the NoAnnotatedError first
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains(r'\(/|\)*' + fileName)]
    manifestDir = fileDF["manifest_dir"].iloc[0]
    # Search thumbnail in dataframe with same manifest_dir as scafflod
    # If found, set it as isSourceOf
    # If not, search file 

    mDF = pd.read_excel(os.path.join(manifestDir, "manifest.xlsx"))
    if SOURCE_OF_COLUMN not in mDF.columns:
        mDF[SOURCE_OF_COLUMN] = ""
    # TODO Change to Views
    viewNames = mDF["filename"][mDF["additional types"] == mime]

    if viewNames.empty:
        # Search from files
        viewLocations = []
        if mime == SCAFFOLD_VIEW_MIME:
            viewLocations = OnDiskFiles().get_scaffold_data().get_view_files()
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            viewLocations = OnDiskFiles().get_scaffold_data().get_thumbnail_files()
        viewNames = [os.path.relpath(view, manifestDir) for view in viewLocations]

    mDF.loc[mDF["filename"].str.contains(r'\(/|\)*' + fileName), SOURCE_OF_COLUMN] = ','.join(viewNames)
    # else:
    # Find the manifest file contain the file annotation
    # mDF = pd.read_excel(io)
    # TODO
    mDF.to_excel(os.path.join(manifestDir, "manifest.xlsx"), index=False, header=True)


def update_derived_from(file_location, mime):
    manifestDataFrame = ManifestDataFrame().get_manifest()
    # fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    # Before add view, the scaffold metadata must already been annotated in manifest, otherwise fix the NoAnnotatedError first
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains(r'\(/|\)*' + fileName)]
    manifestDir = fileDF["manifest_dir"].iloc[0]
    # Search thumbnail in dataframe with same manifest_dir as scafflod
    # If found, set it as isSourceOf
    # If not, search file 
    mDF = pd.read_excel(os.path.join(manifestDir, "manifest.xlsx"))
    if DERIVED_FROM_COLUMN not in mDF.columns:
        mDF[DERIVED_FROM_COLUMN] = ""
    # TODO Change to Views
    parentMime = SCAFFOLD_VIEW_MIME
    if mime == SCAFFOLD_VIEW_MIME:
        parentMime = SCAFFOLD_FILE_MIME
    viewNames = mDF["filename"][mDF[ADDITIONAL_TYPES_COLUMN] == parentMime]

    if viewNames.empty:
        # Search from files
        viewLocations = []
        if parentMime == SCAFFOLD_VIEW_MIME:
            viewLocations = OnDiskFiles().get_scaffold_data().get_view_files()
        elif parentMime == SCAFFOLD_FILE_MIME:
            viewLocations = OnDiskFiles().get_scaffold_data().get_metadata_files()
        viewNames = [os.path.relpath(view, manifestDir) for view in viewLocations]

    mDF.loc[mDF["filename"].str.contains(r'\(/|\)*' + fileName), DERIVED_FROM_COLUMN] = ','.join(viewNames)
    # else:
    # Find the manifest file contain the file annotation
    # mDF = pd.read_excel(io)
    # TODO
    mDF.to_excel(os.path.join(manifestDir, "manifest.xlsx"), index=False, header=True)


def update_additional_type(file_location, file_mime):
    # TODO try not read all the manifest again
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains(r'\(/|\)*' + fileName)]
    # If fileDF is empty, means there's no manifest file contain this file.
    # Check if there's manifest file under same dir. Add file to the manifest.
    # If no manifest file create new manifest file
    if fileDF.empty:
        # Check if there's manifest file under Scaffold File Dir
        newRow = pd.DataFrame({"filename": fileName, "additional types": file_mime}, index=[1])
        if not manifestDataFrame[manifestDataFrame["manifest_dir"] == fileDir].empty:
            mDF = pd.read_excel(os.path.join(fileDir, "manifest.xlsx"))
            newRow = mDF.append(newRow, ignore_index=True)
        newRow.to_excel(os.path.join(fileDir, "manifest.xlsx"), index=False, header=True)

    for index, row in fileDF.iterrows():
        fileLocation = os.path.join(row["manifest_dir"], row['filename'])
        if is_same_file(file_location, fileLocation):
            mDF = pd.read_excel(os.path.join(row["manifest_dir"], "manifest.xlsx"), sheet_name=row["sheet_name"])
            if ADDITIONAL_TYPES_COLUMN not in mDF.columns:
                mDF[ADDITIONAL_TYPES_COLUMN] = ""
            mDF.loc[mDF["filename"] == row['filename'], ADDITIONAL_TYPES_COLUMN] = file_mime
            mDF.to_excel(os.path.join(row["manifest_dir"], "manifest.xlsx"), sheet_name=row["sheet_name"], index=False, header=True)


def fix_error(error):
    checked_locations = []
    for manifest_dir in ManifestDataFrame().get_manifest()['manifest_dir']:
        if manifest_dir not in checked_locations:
            checked_locations.append(manifest_dir)
            if not os.access(manifest_dir, os.W_OK):
                raise AnnotationDirectoryNoWriteAccess(f"Cannot write to directory {manifest_dir}.")

    # Check incorrect annotation before no annotation
    if isinstance(error, IncorrectAnnotationError):
        update_additional_type(error.get_location(), None)
    elif isinstance(error, NotAnnotatedError):
        update_additional_type(error.get_location(), error.get_mime())
    elif isinstance(error, NoViewError):
        set_source_of_column(error.get_location(), SCAFFOLD_VIEW_MIME)
    elif isinstance(error, NoThumbnailError):
        set_source_of_column(error.get_location(), SCAFFOLD_THUMBNAIL_MIME)
    elif isinstance(error, NoDerivedFromError):
        update_derived_from(error.get_location(), error.get_mime())


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

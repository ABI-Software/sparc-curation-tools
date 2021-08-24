import argparse
import json
import math
import os
import pandas as pd
from pathlib import Path
import re

VERSION = '1.1.0'


SCAFFOLD_DIR_MIME = 'inode/vnd.abi.scaffold+directory'
SCAFFOLD_FILE_MIME = 'inode/vnd.abi.scaffold+file'
SCAFFOLD_THUMBNAIL_MIME= 'inode/vnd.abi.scaffold.thumbnail+file'
SCAFFOLD_VIEW_MIME = 'inode/vnd.abi.scaffold.view+file'
TARGET_MIMES = [SCAFFOLD_DIR_MIME, SCAFFOLD_FILE_MIME, SCAFFOLD_THUMBNAIL_MIME]

SIZE_NAME = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

FILENAME_COLUMN = 'filename'
ADDITIONAL_TYPES_COLUMN = 'additional types'
SOURCE_OF_COLUMN = 'isSourceOf'
DERIVED_FROM_COLUMN = 'isDerivedFrom'

FILE_LOCATION_COLUMN = 'file_location'
THUMBNAIL_LOCATION_COLUMN = 'thumbnail_location'
IS_SCAFFOLD_COLUMN = 'isScaffold'


class ScaffoldAnnotationError(object):

    def __init__(self, message, location):
        self._message = message
        self._location = location
    
    def get_location(self):
        return self._location

    def get_error_message(self):
        return f'Error: {self._message}'

    # def __str__(self):
    #     return f'Error: {self._message}'

class NotAnnotatedError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f"Found scaffold metadata file that is not annotated '{location}'."
        super(NotAnnotatedError, self).__init__(message, location)

class NoThumbnailError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f"Found scaffold metadata file that has no thumbnail'{location}'."
        super(NoThumbnailError, self).__init__(message, location)

class NoDerivedFromError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f"Found thumbnail that has no scaffold metadata file '{location}'."
        super(NoDerivedFromError, self).__init__(message, location)

class NotAScaffoldError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f'Scaffold "{location}" either does not exist or is not a scaffold.'
        super(NotAScaffoldError, self).__init__(message, location)

class NotADirError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f'Directory "{location}" either does not exist or is not a directory.'
        super(NotADirError, self).__init__(message, location)

class NotAFileError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = "Not File"
        super(NotADirError, self).__init__(message, location)

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ManifestDataFrame(metaclass=Singleton):
    dataFrame_dir = ""
    _manifestDataFrame = None
    _realScaffoldDF = None
    
    def setup_dataframe(self, dataset_dir, max_size):
        self.read_manifest(dataset_dir)
        search_for_metadata_files(dataset_dir, max_size)
        self.setup_data()
        return self

    def read_manifest(self, dataset_dir):
        self._annotatedScaffoldList = None
        self._realScaffoldList = None
        dataFrame_dir = dataset_dir
        result = list(Path(dataset_dir).rglob("manifest.xlsx"))
        self._manifestDataFrame = pd.DataFrame()
        for r in result:
            xl_file = pd.ExcelFile(r)
            # print(xl_file)
            for sheet_name in xl_file.sheet_names:
                currentDataFrame = xl_file.parse(sheet_name)
                currentDataFrame['sheet_name'] =sheet_name
                currentDataFrame['manifest_dir'] =os.path.dirname(r)
                self._manifestDataFrame = pd.concat([currentDataFrame,self._manifestDataFrame])
        # print(manifestDataFrame)
        self._manifestDataFrame[FILE_LOCATION_COLUMN] = self._manifestDataFrame.apply(lambda row: os.path.join(row['manifest_dir'], row[FILENAME_COLUMN]) if pd.notnull(row[FILENAME_COLUMN]) else None, axis=1)
        if SOURCE_OF_COLUMN in self._manifestDataFrame[self._manifestDataFrame.notna()]:
            # print(self._manifestDataFrame)
            self._manifestDataFrame[THUMBNAIL_LOCATION_COLUMN] = self._manifestDataFrame.apply(lambda row: os.path.join(row['manifest_dir'], row[SOURCE_OF_COLUMN]) if pd.notnull(row[SOURCE_OF_COLUMN]) else None, axis=1) 
        return self._manifestDataFrame

    def get_manifest(self):
        return self._manifestDataFrame

    def setup_data(self):
        self._annotatedScaffoldList = [ScaffoldMetadata(row) for i, row in self._manifestDataFrame[self._manifestDataFrame[ADDITIONAL_TYPES_COLUMN] == SCAFFOLD_FILE_MIME].iterrows()]
        # TODO Get directly from files by search_for_metadata_files function
        self._realScaffoldList = [ScaffoldMetadata(row) for i, row in self._manifestDataFrame[self._manifestDataFrame[IS_SCAFFOLD_COLUMN] == True].iterrows()]

    # TODO Get ScaffoldMetadata by search_for_metadata_files function and Delete this function.
    def set_true_scaffold(self, file_location):
        # print("set true scaffold", file_location)
        # self._manifestDataFrame.to_excel("manifestTest.xlsx")
        # print(file_location)
        fileInDF = self._manifestDataFrame.apply(lambda row: self.check_samefile(file_location, row[FILE_LOCATION_COLUMN]), axis = 1)
        if IS_SCAFFOLD_COLUMN not in self._manifestDataFrame.columns:
            self._manifestDataFrame[IS_SCAFFOLD_COLUMN] = False
        if fileInDF.any():
            # print("set in mani", file_location)
            self._manifestDataFrame[IS_SCAFFOLD_COLUMN][fileInDF] = True
        else:
            print("set manifest file loc not in mani", file_location)
            newRow = {FILENAME_COLUMN:os.path.basename(file_location), FILE_LOCATION_COLUMN: file_location, IS_SCAFFOLD_COLUMN: True}
            self._manifestDataFrame = self._manifestDataFrame.append(newRow, ignore_index=True)

    def check_samefile(self, loc1, loc2):
        if pd.notnull(loc2):
            if os.path.isfile(loc2):
                return os.path.samefile(loc1,loc2)
        return False

    def get_real_scaffold(self):
        # Return a Series of filename
        return self._realScaffoldList

    def get_annotated_scaffold(self):
        # Return a Series of filename
        return self._annotatedScaffoldList

    def get_false_real_scaffold(self):
        # Return a Series of filename
        # return self._manifestDataFrame[(self._manifestDataFrame[IS_SCAFFOLD_COLUMN] == False) & (self._manifestDataFrame[ADDITIONAL_TYPES_COLUMN] == SCAFFOLD_FILE_MIME)]
        result = [] 
        for i in self._annotatedScaffoldList:
            if i  not in self._realScaffoldList:
                result.append(i)
        return result

    def get_unannotated_scaffold(self):
        # Return a Series of filename
        # return self._manifestDataFrame[(self._manifestDataFrame[IS_SCAFFOLD_COLUMN] == True) & (self._manifestDataFrame[ADDITIONAL_TYPES_COLUMN] != SCAFFOLD_FILE_MIME)]
        result = []
        for i in self._realScaffoldList:
            if i  not in self._annotatedScaffoldList:
                result.append(i)
        return result

    def get_real_scaffold_no_thumbnail(self):
        return self._manifestDataFrame[(self._manifestDataFrame[IS_SCAFFOLD_COLUMN] == True) & (pd.isnull(self._manifestDataFrame[THUMBNAIL_LOCATION_COLUMN]))]


class ScaffoldMetadata(object):
    '''
    TODO use this class to wrap one dataframe row to an object.
    '''

    def __init__(self, dfRow):
        self._dir = dfRow[FILE_LOCATION_COLUMN]
        self._file = dfRow[FILENAME_COLUMN]
        self._thumbnail = dfRow[THUMBNAIL_LOCATION_COLUMN]
        self._location = dfRow[FILE_LOCATION_COLUMN]
        self._views = None
        if isinstance(dfRow[SOURCE_OF_COLUMN],str):
            self._views = [ScaffoldView(item) for item in dfRow[SOURCE_OF_COLUMN].split(',')]

    def get_location(self):
        post_fix = list(filter(None, [self._dir, self._file, self._thumbnail]))
        return os.path.normpath(os.path.join(self._location, post_fix[0]))

    def set_dir(self, dir_name):
        self._dir = dir_name

    def get_dir(self):
        return self._dir

    def set_file(self, file):
        self._file = file

    def get_file(self):
        return self._file

    def set_thumbnail(self, thumbnail):
        self._thumbnail = thumbnail

    def get_thumbnail(self):
        return self._thumbnail

    def add_view(self, thumbnail):
        self._views = thumbnail

    def remove_view(self, thumbnail):
        self._views = thumbnail

    def get_views(self):
        return self._views

    def __eq__(self, other):
        return os.path.samefile(self.get_location() , other.get_location())

class ScaffoldView(object):
    '''
    TODO use this class to wrap one dataframe row to an object.
    '''

    def __init__(self, dfRow):
        self._fileName = dfRow

    def get_location(self):
        post_fix = list(filter(None, [self._dir, self._file, self._thumbnail]))
        return os.path.normpath(os.path.join(self._location, post_fix[0]))

    def set_thumbnail(self, thumbnail):
        self._thumbnail = thumbnail

    def get_thumbnail(self):
        return self._thumbnail

def create_scaffold_annotation(df):
    value = None
    base_dir = df['manifest_dir']
    filename = df['filename']
    mime = df['additional types']
    if mime in TARGET_MIMES:
        value = ScaffoldMetadata(base_dir)
        if mime == SCAFFOLD_DIR_MIME:
            value.set_dir(filename)
        elif mime == SCAFFOLD_FILE_MIME:
            value.set_file(filename)
            if SOURCE_OF_COLUMN in df[df.notna()]:
                value.set_thumbnail(os.path.join(base_dir,df[SOURCE_OF_COLUMN]))
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            value.set_thumbnail(filename)
        if not value.file():
            value = None
    return value


def check_scaffold_annotations(scaffold_annotations):
    errors = []
    for scaffold_annotation in scaffold_annotations:
        location = scaffold_annotation.location()
        if scaffold_annotation.is_dir():
            if not os.path.isdir(location):
                errors.append(NotADirError(location))
        elif not os.path.isfile(location):
            errors.append(ScaffoldAnnotationError(f'File "{location}" does not exist.', location))
    return errors


def search_for_metadata_files(dataset_dir, max_size):
    metadata = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        meta = False
        if os.path.getsize(r) < max_size and os.path.isfile(r):
            try:
                with open(r, encoding='utf-8') as f:
                    file_data = f.read()
            except UnicodeDecodeError:
                continue
            except IsADirectoryError:
                continue

            try:
                data = json.loads(file_data)
                if data:
                    if isinstance(data, list):
                        url_present = True
                        for d in data:
                            if 'URL' not in d:
                                url_present = False

                        meta = url_present
            except json.decoder.JSONDecodeError:
                pass

        if meta:
            # metadata.append(ScaffoldMetadata(os.path.dirname(r), file=os.path.split(r)[1]))
            ManifestDataFrame().set_true_scaffold(r)

    # return metadata

def search_thumbnail_files(dataset_dir):
    result = list(Path(dataset_dir).rglob("thumbnail*"))
    # print(result)
    return result[0]

def check_scaffold_metadata_annotated():
    errors = []
    # print(ManifestDataFrame().get_unannotated_scaffold())
    for row in ManifestDataFrame().get_unannotated_scaffold():
        errors.append(NotAnnotatedError(row.get_location()))
    for row in ManifestDataFrame().get_false_real_scaffold():
        errors.append(NotAScaffoldError(row.get_location()))
    return errors

def check_scaffold_thumbnail_annotated():
    errors = []
    manifestDataFrame = ManifestDataFrame()
    # scaffoldDF = manifestDataFrame[manifestDataFrame["additional types"]==SCAFFOLD_FILE_MIME]
    for index, row in manifestDataFrame.get_real_scaffold_no_thumbnail().iterrows():
        errors.append(NoThumbnailError(row[FILE_LOCATION_COLUMN]))
    return errors

def get_none_rows(df,column):
    if column in df.columns:
        df = df[df[column].isnull()]
    return df

def get_confirmation_message(error):
    '''
    "To fix this error, the 'additional types' of 'filename' in 'manifestFile' will be set to 'MIME'."
    "To fix this error, a manifestFile will be created under manifestDir, and will insert the filename in this manifestFile with 'additional types' MIME."

    "To fix this error, the data of filename in manifestFile will be deleted."
    # TODO or NOT TODO: return different message based on input error type
    '''
    message = "Let this magic tool fix this error for you."
    return message

def get_errors():
    errors = []
    errors.extend(check_scaffold_metadata_annotated())
    errors.extend(check_scaffold_thumbnail_annotated())
    return errors

def fix_error(error):
    # TODO different way to fix error based on input error type
    if isinstance(error, NotAnnotatedError):
        annotate_scaffold_file(error.get_location())
    elif isinstance(error, NoThumbnailError):
        add_thumbnail_to_scafflod(error.get_location())
    elif isinstance(error, NotAScaffoldError):
        remove_wrong_annotation(error.get_location())


def add_thumbnail_to_scafflod(file_location):
    # TODO try not read all the manifest again
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    fileDF = manifestDataFrame[manifestDataFrame["filename"] == fileName]
    # Search thumbnail in dataframe with same manifest_dir as scafflod
    # If found, set it as isSourceOf
    # If not, search file 

    # Check if there's manifest file under Scaffold File Dir First
    if not manifestDataFrame[manifestDataFrame["manifest_dir"] == fileDir].empty:
        mDF = pd.read_excel(os.path.join(fileDir,"manifest.xlsx"))
        if SOURCE_OF_COLUMN not in mDF.columns:
            mDF[SOURCE_OF_COLUMN] = ""
        thumbnailName = mDF["filename"][mDF["additional types"]==SCAFFOLD_THUMBNAIL_MIME]
        # print(mDF)
        print(thumbnailName)
        if thumbnailName.empty:
            # Search from files
            thumbnailName = "thumbnail.png"
            thumbnailName = os.path.basename(search_thumbnail_files(fileDir))
        else:
            thumbnailName = thumbnailName.iloc[0]
        mDF[SOURCE_OF_COLUMN][mDF["filename"]==fileName] = thumbnailName
    else:
        # Find the manifest file contain the file annotation
        mDF = pd.read_excel(io)
    mDF.to_excel(os.path.join(fileDir,"manifest.xlsx"), index=False, header=True)


def annotate_scaffold_file(file_location):
    # TODO try not read all the manifest again
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    fileDF = manifestDataFrame[manifestDataFrame["filename"] == fileName]
    # If fileDF is empty, means there's no manifest file contain this file. 
    # Check if there's manifest file under same dir. Add file to the manifest.
    # If no manifest file create new manifest file
    if fileDF.empty:
        # Check if there's manifest file under Scaffold File Dir
        newRow = pd.DataFrame({"filename":fileName,"additional types":SCAFFOLD_FILE_MIME},index = [1])
        if not manifestDataFrame[manifestDataFrame["manifest_dir"] == fileDir].empty:
            mDF = pd.read_excel(os.path.join(fileDir,"manifest.xlsx"))
            newRow = mDF.append(newRow,ignore_index=True)
        newRow.to_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"), sheet_name=row["sheet_name"], index=False, header=True)

    print(fileDF)
    # insert_additional_types(fileDF)
    
# def add_additional_types(fileDF):
    for index, row in fileDF.iterrows():
        fileLocation = os.path.join(row["manifest_dir"], row['filename'])
        if os.path.samefile(file_location, fileLocation):
            mDF = pd.read_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"),sheet_name=row["sheet_name"])
            mDF['additional types'][mDF["filename"] == row['filename']] = SCAFFOLD_FILE_MIME
            mDF.to_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"), sheet_name=row["sheet_name"], index=False, header=True)

def remove_wrong_annotation(file_location):
    # TODO try not read all the manifest again
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains('\(/|\\)*' + fileName)== True]

    print("remove_wrong_annotation " , fileDF)
    # insert_additional_types(fileDF)

# def add_additional_types(fileDF):
    for index, row in fileDF.iterrows():
        fileLocation = os.path.join(row["manifest_dir"], row['filename'])
        if os.path.samefile(file_location, fileLocation):
            mDF = pd.read_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"),sheet_name=row["sheet_name"])
            mDF['additional types'][mDF["filename"] == row['filename']] = ""
            mDF.to_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"), sheet_name=row["sheet_name"], index=False, header=True)

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s}{SIZE_NAME[i]}"


def convert_to_bytes(size_string):
    m = re.match(r'^(\d+)(B|KiB|MiB|GiB|PiB|EiB|ZiB|YiB)$', size_string)
    if not m:
        raise argparse.ArgumentTypeError("'" + size_string + "' is not a valid size. Expected forms like '5MiB', '3KiB', '400B'.")
    start = m.group(1)
    end = m.group(2)
    return int(start) * math.pow(1024, SIZE_NAME.index(end))


def main():
    parser = argparse.ArgumentParser(description='Check scaffold annotations for a SPARC dataset.')
    parser.add_argument("dataset_dir", help='directory to check.')
    parser.add_argument("-m", "--max-size", help="Set the max size for metadata file. Default is 2MiB", default='2MiB', type=convert_to_bytes)

    # args = parser.parse_args()
    dataset_dir = r"C:\Users\ywan787\neondata\curationdata"
    max_size = 1000000000

    ManifestDataFrame().setup_dataframe(dataset_dir, max_size)
    search_for_metadata_files(dataset_dir, max_size)

    # errors = check_scaffold_annotations()
    errors = get_errors()

    for error in errors:
        print(error.get_error_message())
        if isinstance(error, NotAScaffoldError):
            remove_wrong_annotation(errors[0].get_location())
            return
    print(ManifestDataFrame().get_real_scaffold())


if __name__ == "__main__":
    main()

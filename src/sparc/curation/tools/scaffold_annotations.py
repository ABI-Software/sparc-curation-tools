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
SCAFFOLD_VIEW_MIME = 'inode/vnd.abi.scaffold.view+file'
SCAFFOLD_THUMBNAIL_MIME= 'inode/vnd.abi.scaffold.thumbnail+file'
TARGET_MIMES = [SCAFFOLD_DIR_MIME, SCAFFOLD_FILE_MIME, SCAFFOLD_THUMBNAIL_MIME]

SIZE_NAME = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

FILENAME_COLUMN = 'filename'
ADDITIONAL_TYPES_COLUMN = 'additional types'
MANIFEST_DIR_COLUMN = 'manifest_dir'
SOURCE_OF_COLUMN = 'isSourceOf'
DERIVED_FROM_COLUMN = 'isDerivedFrom'
FILE_LOCATION_COLUMN = 'file_location'


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
    def __init__(self, location, mime):
        self._mime = mime
        if mime == SCAFFOLD_FILE_MIME:
            fileType = "Metadata"
        elif mime == SCAFFOLD_VIEW_MIME:
            fileType = "View"    
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            fileType = "Thumbnail"  
        message = f"Found Scaffold '{fileType}' file that is not annotated '{location}'."
        super(NotAnnotatedError, self).__init__(message, location)
    
    def get_mime(self):
        return self._mime

class NoViewError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f"Found scaffold metadata file that has no view'{location}'."
        super(NoViewError, self).__init__(message, location)

class NoThumbnailError(ScaffoldAnnotationError):
    def __init__(self, location):
        message = f"Found scaffold view file that has no thumbnail'{location}'."
        super(NoThumbnailError, self).__init__(message, location)

class NoDerivedFromError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        self._mime = mime
        if mime == SCAFFOLD_FILE_MIME:
            fileType = "Metadata"
        elif mime == SCAFFOLD_VIEW_MIME:
            fileType = "View"    
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            fileType = "Thumbnail"  
        message = f"Found '{fileType}' that has no derived from file '{location}'."
        super(NoDerivedFromError, self).__init__(message, location)
    
    def get_mime(self):
        return self._mime
        
class WrongAnnotatedError(ScaffoldAnnotationError):
    def __init__(self, location, mime):
        self._mime = mime
        if mime == SCAFFOLD_FILE_MIME:
            fileType = "Metadata"
        elif mime == SCAFFOLD_VIEW_MIME:
            fileType = "View"    
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            fileType = "Thumbnail"  
        message = f'File "{location}" either does not exist or is not a scaffold "{fileType}".'
        super(WrongAnnotatedError, self).__init__(message, location)
    
    def get_mime(self):
        return self._mime

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
        self.setup_data(dataset_dir, max_size)
        return self

    def read_manifest(self, dataset_dir):
        self._annotatedFileList = None
        self._realScaffoldList = None
        self.dataFrame_dir = dataset_dir
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
        return self._manifestDataFrame

    def get_manifest(self):
        return self._manifestDataFrame

    def setup_data(self, dataset_dir, max_size):
        self._annotatedFileList = [ScaffoldAnnotation(row) for i, row in self._manifestDataFrame[self._manifestDataFrame[ADDITIONAL_TYPES_COLUMN].notnull()].iterrows()]
        self._annotatedFileLocList = [i.get_location() for i in self._annotatedFileList]

        # real file should only return location links, coz they don't have view or any other info
        self._realScaffoldList = search_for_metadata_files(dataset_dir, max_size)
        self._realViewList = search_view_files(self.dataFrame_dir)
        self._realThumbnailList = search_thumbnail_files(self.dataFrame_dir)

    def check_samefile(self, loc1, loc2):
        if pd.notnull(loc2):
            if os.path.isfile(loc2):
                return os.path.samefile(loc1,loc2)
        return False

    def get_real_scaffold(self):
        # Return a Series of filename
        return [os.path.basename(location) for location in self._realScaffoldList]

    def get_annotated_scaffold(self):
        result = []
        for i in self._annotatedFileList:
            if i._additionalType == SCAFFOLD_FILE_MIME:
                result.append(i)
        return result

    def get_annotated_view(self):
        result = []
        for i in self._annotatedFileList:
            if i._additionalType == SCAFFOLD_VIEW_MIME:
                result.append(i)
        return result

    def get_wrong_annotated_errors(self):
        errors = [] 
        for i in self._annotatedFileList:
            if i._additionalType == SCAFFOLD_FILE_MIME:
                if i.get_location() not in self._realScaffoldList:
                    errors.append(WrongAnnotatedError(i.get_location(), i._additionalType))
            
            if i._additionalType == SCAFFOLD_VIEW_MIME:
                if i.get_location() not in self._realViewList:
                    errors.append(WrongAnnotatedError(i.get_location(), i._additionalType))

            if i._additionalType == SCAFFOLD_THUMBNAIL_MIME:
                if i.get_location() not in self._realThumbnailList:
                    errors.append(WrongAnnotatedError(i.get_location(), i._additionalType))
        return errors

    def get_unannotated_errors(self):
        errors = []

        for i in self._realScaffoldList:
            if i not in self._annotatedFileLocList:
                errors.append(NotAnnotatedError(i, SCAFFOLD_FILE_MIME))

        for i in self._realViewList:
            if i not in self._annotatedFileLocList:
                errors.append(NotAnnotatedError(i, SCAFFOLD_VIEW_MIME))
        
        for i in self._realThumbnailList:
            if i not in self._annotatedFileLocList:
                errors.append(NotAnnotatedError(i, SCAFFOLD_THUMBNAIL_MIME))
        
        return errors

    def get_real_scaffold_no_view(self):
        result = []
        for i in self._annotatedFileList:
            if i.get_location() in self._realScaffoldList and not i.get_children():
                result.append(i)
        return result

    def get_view_no_thumbnail(self):
        result = []
        for i in self._annotatedFileList:
            if i.get_location() in self._realViewList and not i.get_children():
                result.append(i)
        return result

    def get_view_no_scaffold(self):
        result = []
        for i in self._annotatedFileList:
            if i.get_location() in self._realViewList and not i.get_parent():
                result.append(i)
        return result

    def get_thumbnail_no_view(self):
        result = []
        for i in self._annotatedFileList:
            if i.get_location() in self._realThumbnailList and not i.get_parent():
                result.append(i)
        return result


class ScaffoldAnnotation(object):
    '''
    TODO use this class to wrap one dataframe row to an object.
    Only rows with ADDITIONAL_TYPES_COLUMN will be wrapped by this class
    '''

    def __init__(self, dfRow):
        self._dir = dfRow[FILE_LOCATION_COLUMN] # ??? I forget what's this for
        self._manifestDir = dfRow[MANIFEST_DIR_COLUMN]
        self._fileName = dfRow[FILENAME_COLUMN]
        self._location = dfRow[FILE_LOCATION_COLUMN]
        self._additionalType = None
        self._children = None
        self._parent = None

        if ADDITIONAL_TYPES_COLUMN in dfRow:
            if isinstance(dfRow[ADDITIONAL_TYPES_COLUMN],str):
                self._additionalType = dfRow[ADDITIONAL_TYPES_COLUMN]

        if SOURCE_OF_COLUMN in dfRow:
            if isinstance(dfRow[SOURCE_OF_COLUMN],str):
                self._children = [str(os.path.join(self._manifestDir, filename)) for filename in dfRow[SOURCE_OF_COLUMN].split(',')]

        if DERIVED_FROM_COLUMN in dfRow:
            if isinstance(dfRow[DERIVED_FROM_COLUMN],str):
                self._parent = str(os.path.join(self._manifestDir, dfRow[DERIVED_FROM_COLUMN]))

    def get_location(self):
        return os.path.normpath(os.path.join(self._location))

    def set_dir(self, dir_name):
        self._dir = dir_name

    def get_dir(self):
        return self._dir

    def set_filename(self, file):
        self._fileName = file

    def get_filename(self):
        return self._fileName

    def get_children(self):
        return self._children

    def get_parent(self):
        return self._parent

    def get_thumbnail(self):
        return self._children[0]

    def __eq__(self, other):
        return os.path.samefile(self.get_location() , other.get_location())

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
            metadata.append(str(r))

    return metadata

def search_thumbnail_files(dataset_dir):
    result = list(Path(dataset_dir).rglob("thumbnail*"))
    return [str(x) for x in result]

def search_view_files(dataset_dir):
    result = list(Path(dataset_dir).rglob("*view*.json"))
    return [str(x) for x in result]

def check_additional_types_annotated():
    errors = []
    errors += ManifestDataFrame().get_unannotated_errors()
    errors += ManifestDataFrame().get_wrong_annotated_errors()
    return errors

def check_scaffold_view_annotated():
    errors = []
    manifestDataFrame = ManifestDataFrame()
    # scaffoldDF = manifestDataFrame[manifestDataFrame["additional types"]==SCAFFOLD_FILE_MIME]
    for scaffoldAnnotation in manifestDataFrame.get_real_scaffold_no_view():
        errors.append(NoViewError(scaffoldAnnotation.get_location()))
    for scaffoldAnnotation in manifestDataFrame.get_view_no_scaffold():
        errors.append(NoDerivedFromError(scaffoldAnnotation.get_location(), SCAFFOLD_VIEW_MIME))
    # Check if the view annotated wrong
    # for scaffoldAnnotation in manifestDataFrame.get_real_scaffold_no_view():
    #     errors.append(NoViewError(scaffoldAnnotation.get_location()))
    return errors

def check_scaffold_thumbnail_annotated():
    errors = []
    manifestDataFrame = ManifestDataFrame()
    # scaffoldDF = manifestDataFrame[manifestDataFrame["additional types"]==SCAFFOLD_FILE_MIME]

    for viewAnnotation in manifestDataFrame.get_view_no_thumbnail():
        errors.append(NoThumbnailError(viewAnnotation.get_location()))
    for scaffoldAnnotation in manifestDataFrame.get_thumbnail_no_view():
        errors.append(NoDerivedFromError(scaffoldAnnotation.get_location(), SCAFFOLD_THUMBNAIL_MIME))
    # Check if the thumbnail annotated wrong
    # for scaffoldAnnotation in manifestDataFrame.get_real_scaffold_no_thumbnail():
    #     errors.append(NoThumbnailError(scaffoldAnnotation.get_location()))
    return errors

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
    errors.extend(check_additional_types_annotated())
    errors.extend(check_scaffold_view_annotated())
    errors.extend(check_scaffold_thumbnail_annotated())
    return errors

def fix_error(error):
    # Check wrong annotation before no annotation
    if isinstance(error, WrongAnnotatedError):
        update_additional_type(error.get_location(), None)
    elif isinstance(error, NotAnnotatedError):
        update_additional_type(error.get_location(), error.get_mime())
    elif isinstance(error, NoViewError):
        set_source_of_column(error.get_location(), SCAFFOLD_VIEW_MIME)    
    elif isinstance(error, NoThumbnailError):
        set_source_of_column(error.get_location(), SCAFFOLD_THUMBNAIL_MIME)
    elif isinstance(error, NoDerivedFromError):
        update_derived_from(error.get_location(), error.get_mime())        

def set_source_of_column(file_location, mime):
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    # Before add view, the scaffold metadata must already been annotated in manifest, otherwise fix the NoAnnotatedError first
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains('\(/|\\)*' + fileName)== True]
    manifestDir = fileDF["manifest_dir"].iloc[0]
    # Search thumbnail in dataframe with same manifest_dir as scafflod
    # If found, set it as isSourceOf
    # If not, search file 

    mDF = pd.read_excel(os.path.join(manifestDir,"manifest.xlsx"))
    if SOURCE_OF_COLUMN not in mDF.columns:
        mDF[SOURCE_OF_COLUMN] = ""
    # TODO Change to Views
    viewNames = mDF["filename"][mDF["additional types"]==mime]

    if viewNames.empty:
        # Search from files
        if mime == SCAFFOLD_VIEW_MIME:
            viewLocations = search_view_files(fileDir)
        elif mime == SCAFFOLD_THUMBNAIL_MIME:
            viewLocations = search_thumbnail_files(fileDir)
        viewNames = [os.path.relpath(view, manifestDir) for view in viewLocations]
    print(viewNames)
    mDF[SOURCE_OF_COLUMN][mDF["filename"].str.contains('\(/|\\)*' + fileName)== True] = ','.join(viewNames)
    # else:
        # Find the manifest file contain the file annotation
        # mDF = pd.read_excel(io)
        # TODO
    mDF.to_excel(os.path.join(manifestDir,"manifest.xlsx"), index=False, header=True)

def update_derived_from(file_location, mime):
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    # Before add view, the scaffold metadata must already been annotated in manifest, otherwise fix the NoAnnotatedError first
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains('\(/|\\)*' + fileName)== True]
    manifestDir = fileDF["manifest_dir"].iloc[0]
    # Search thumbnail in dataframe with same manifest_dir as scafflod
    # If found, set it as isSourceOf
    # If not, search file 
    mDF = pd.read_excel(os.path.join(manifestDir,"manifest.xlsx"))
    if DERIVED_FROM_COLUMN not in mDF.columns:
        mDF[DERIVED_FROM_COLUMN] = ""
    # TODO Change to Views
    parentMime = SCAFFOLD_VIEW_MIME
    if mime == SCAFFOLD_VIEW_MIME:
        parentMime = SCAFFOLD_FILE_MIME
    viewNames = mDF["filename"][mDF[ADDITIONAL_TYPES_COLUMN]==parentMime]

    if viewNames.empty:
        # Search from files
        if parentMime == SCAFFOLD_VIEW_MIME:
            viewLocations = search_view_files(fileDir)
        elif parentMime == SCAFFOLD_FILE_MIME:
            viewLocations = search_for_metadata_files(fileDir, 200000)
        viewNames = [os.path.relpath(view, manifestDir) for view in viewLocations]
    print(viewNames)
    mDF[DERIVED_FROM_COLUMN][mDF["filename"].str.contains('\(/|\\)*' + fileName)== True] = ','.join(viewNames)
    # else:
        # Find the manifest file contain the file annotation
        # mDF = pd.read_excel(io)
        # TODO
    mDF.to_excel(os.path.join(manifestDir,"manifest.xlsx"), index=False, header=True)

def update_additional_type(file_location, fileMime):
    # TODO try not read all the manifest again
    manifestDataFrame = ManifestDataFrame().get_manifest()
    fileDir = os.path.dirname(file_location)
    fileName = os.path.basename(file_location)
    fileDF = manifestDataFrame[manifestDataFrame["filename"].str.contains('\(/|\\)*' + fileName)== True]
    # If fileDF is empty, means there's no manifest file contain this file. 
    # Check if there's manifest file under same dir. Add file to the manifest.
    # If no manifest file create new manifest file
    if fileDF.empty:
        # Check if there's manifest file under Scaffold File Dir
        newRow = pd.DataFrame({"filename":fileName,"additional types":fileMime},index = [1])
        if not manifestDataFrame[manifestDataFrame["manifest_dir"] == fileDir].empty:
            mDF = pd.read_excel(os.path.join(fileDir,"manifest.xlsx"))
            newRow = mDF.append(newRow,ignore_index=True)
        newRow.to_excel(os.path.join(fileDir,"manifest.xlsx"), index=False, header=True)

    for index, row in fileDF.iterrows():
        fileLocation = os.path.join(row["manifest_dir"], row['filename'])
        if os.path.samefile(file_location, fileLocation):
            mDF = pd.read_excel(os.path.join(row["manifest_dir"],"manifest.xlsx"),sheet_name=row["sheet_name"])
            if ADDITIONAL_TYPES_COLUMN not in mDF.columns:
                mDF[ADDITIONAL_TYPES_COLUMN] = ""
            print(fileMime)
            mDF[ADDITIONAL_TYPES_COLUMN][mDF["filename"] == row['filename']] = fileMime
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

    errors = get_errors()

    for error in errors:
        print(error.get_error_message())
        fix_error(error)
    print(ManifestDataFrame().get_real_scaffold())
    search_view_files(dataset_dir)


if __name__ == "__main__":
    main()

# VERSION = sparc.curation.tools.__version__

SCAFFOLD_DIR_MIME = 'inode/vnd.abi.scaffold+directory'
SCAFFOLD_FILE_MIME = 'inode/vnd.abi.scaffold+file'
SCAFFOLD_VIEW_MIME = 'inode/vnd.abi.scaffold.view+file'
SCAFFOLD_THUMBNAIL_MIME = 'inode/vnd.abi.scaffold.thumbnail+file'
TARGET_MIMES = [SCAFFOLD_DIR_MIME, SCAFFOLD_FILE_MIME, SCAFFOLD_THUMBNAIL_MIME]

SIZE_NAME = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

FILENAME_COLUMN = 'filename'
ADDITIONAL_TYPES_COLUMN = 'additional types'
MANIFEST_DIR_COLUMN = 'manifest_dir'
SOURCE_OF_COLUMN = 'isSourceOf'
DERIVED_FROM_COLUMN = 'isDerivedFrom'
FILE_LOCATION_COLUMN = 'file_location'

MIMETYPE_TO_FILETYPE_MAP = {
    SCAFFOLD_FILE_MIME: 'Metadata',
    SCAFFOLD_VIEW_MIME: 'View',
    SCAFFOLD_THUMBNAIL_MIME: 'Thumbnail'
}

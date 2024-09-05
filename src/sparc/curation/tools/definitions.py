# VERSION = sparc.curation.tools.__version__

CONTEXT_INFO_MIME = 'application/x.vnd.abi.context-information+json'
PLOT_CSV_MIME = 'text/x.vnd.abi.plot+csv'
PLOT_TSV_MIME = 'text/x.vnd.abi.plot+Tab-separated-values'
SCAFFOLD_DIR_MIME = 'inode/vnd.abi.scaffold+directory'
SCAFFOLD_INFO_MIME = 'application/x.vnd.abi.organ-scaffold-info+json'
SCAFFOLD_META_MIME = 'application/x.vnd.abi.scaffold.meta+json'
SCAFFOLD_VIEW_MIME = 'application/x.vnd.abi.scaffold.view+json'
SCAFFOLD_THUMBNAIL_MIME = 'image/x.vnd.abi.thumbnail+jpeg'
STL_MODEL_MIME = 'model/stl'
VTK_MODEL_MIME = 'model/vtk'

OLD_SCAFFOLD_MIMES = [SCAFFOLD_DIR_MIME, 'inode/vnd.abi.scaffold+file', 'inode/vnd.abi.scaffold+thumbnail']

SIZE_NAME = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

MANIFEST_FILENAME = 'manifest.xlsx'

ADDITIONAL_TYPES_COLUMN = 'additional types'
ANATOMICAL_ENTITY_COLUMN = 'IsAboutAnatomicalEntity'
DERIVED_FROM_COLUMN = 'IsDerivedFrom'
FILE_LOCATION_COLUMN = 'file_location'
FILENAME_COLUMN = 'filename'
MANIFEST_DIR_COLUMN = 'manifest_dir'
SHEET_NAME_COLUMN = 'sheet_name'
SOURCE_OF_COLUMN = 'IsSourceOf'
SUPPLEMENTAL_JSON_COLUMN = 'Supplemental JSON Metadata'

MIMETYPE_TO_FILETYPE_MAP = {
    SCAFFOLD_META_MIME: 'Metadata',
    SCAFFOLD_VIEW_MIME: 'View',
    SCAFFOLD_THUMBNAIL_MIME: 'Thumbnail',
    STL_MODEL_MIME: 'STL Model',
    VTK_MODEL_MIME: 'VTK Model',
    SCAFFOLD_DIR_MIME: 'Directory',
    SCAFFOLD_INFO_MIME: 'ScaffoldInformation',
}

MIMETYPE_TO_PARENT_FILETYPE_MAP = {
    SCAFFOLD_VIEW_MIME: 'Metadata',
    CONTEXT_INFO_MIME: 'Metadata',
    SCAFFOLD_META_MIME: 'ScaffoldInformation',
    SCAFFOLD_THUMBNAIL_MIME: 'View',
    STL_MODEL_MIME: 'View',
    VTK_MODEL_MIME: 'View',
}

MIMETYPE_TO_CHILDREN_FILETYPE_MAP = {
    SCAFFOLD_VIEW_MIME: ['Thumbnail', 'STL Model', 'VTK Model'],
    SCAFFOLD_META_MIME: ['View', 'ContextInfo'],
    SCAFFOLD_INFO_MIME: ['Metadata'],
}
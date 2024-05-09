import csv
import json
import os
from pathlib import Path

from sparc.curation.tools.definitions import STL_MODEL_MIME, VTK_MODEL_MIME
from sparc.curation.tools.helpers.base import Singleton
from sparc.curation.tools.utilities import convert_to_bytes
from sparc.curation.tools.plot_utilities import generate_dataframe_from_txt

ZINC_GRAPHICS_TYPES = ["points", "lines", "surfaces", "contours", "streamlines"]


def is_graphics_entry(entry):
    """
    Check if the given entry in JSON format represents a graphics entry.

    Args:
        entry (dict): The JSON entry to check.

    Returns:
        bool: True if it's a graphics entry, False otherwise.
    """
    if 'URL' in entry and 'Type' in entry:
        entry_type = entry['Type']
        if entry_type.lower() in ZINC_GRAPHICS_TYPES:
            return True

    return False


def is_view_entry(entry):
    """
    Check if the given entry in JSON format represents a view entry.

    Args:
        entry (dict): The JSON entry to check.

    Returns:
        bool: True if it's a view entry, False otherwise.
    """
    if 'URL' in entry and 'Type' in entry:
        entry_type = entry['Type']
        if entry_type.lower() == "view":
            return True

    return False


def contains_metadata(json_data):
    """
    Check if the given JSON data contains metadata entries.

    Args:
        json_data (str): The JSON data to test.

    Returns:
        bool: True if it contains metadata, False otherwise.
    """
    have_viewable_graphics = False
    have_view_reference = False

    if json_data:
        if isinstance(json_data, list):
            for entry in json_data:
                if not have_viewable_graphics and is_graphics_entry(entry):
                    have_viewable_graphics = True
                if not have_view_reference and is_view_entry(entry):
                    have_view_reference = True

    return have_view_reference and have_viewable_graphics


def represents_view(json_data):
    """
    Check if the given JSON data represents a view.

    Args:
        json_data (str): The JSON data to test.

    Returns:
        bool: True if it represents a view, False otherwise.
    """
    is_view = False

    if json_data:
        if isinstance(json_data, dict):
            expected_keys = ["farPlane", "nearPlane", "upVector", "targetPosition", "eyePosition"]
            missing_key = False

            for expected_key in expected_keys:
                if expected_key not in json_data:
                    missing_key = True

            is_view = not missing_key

    return is_view


def is_context_data_file(json_data):
    """
    Check if the given JSON data represents a context data file.

    Args:
        json_data (str): The JSON data to check.

    Returns:
        bool: True if it represents a context data file, False otherwise.
    """
    if json_data:
        if isinstance(json_data, dict):
            if "version" in json_data and "id" in json_data:
                return json_data["id"] == "sparc.science.context_data"

    return False


def is_annotation_csv_file(csv_reader):
    """
    Check if the given CSV reader represents an annotation CSV file.

    Args:
        csv_reader (csv.reader): The CSV reader to check.

    Returns:
        bool: True if it represents an annotation CSV file, False otherwise.
    """
    if csv_reader:
        first = True

        for row in csv_reader:
            if first:
                if len(row) == 2 and row[0] == "Term ID" and row[1] == "Group name":
                    first = False
                else:
                    return False
            elif len(row) != 2:
                return False

        return True

    return False


def is_json_of_type(file_path, max_size, test_func):
    """
    Check if the file at the given path is a JSON file of a specific type.

    Args:
        file_path (str): The path to the file.
        max_size (int): The maximum allowed file size.
        test_func (function): The function to test the JSON data.

    Returns:
        bool: True if it is a JSON file of the specified type, False otherwise.
    """
    result = False

    if os.path.getsize(file_path) < max_size and os.path.isfile(file_path):
        try:
            with open(file_path, encoding='utf-8') as f:
                file_data = f.read()
        except UnicodeDecodeError:
            return result
        except IsADirectoryError:
            return result

        try:
            data = json.loads(file_data)
            result = test_func(data)
        except json.decoder.JSONDecodeError:
            return result

    return result


def is_csv_of_type(file_path, max_size, test_func):
    """
    Check if the file at the given path is a CSV file of a specific type.

    Args:
        file_path (str): The path to the file.
        max_size (int): The maximum allowed file size.
        test_func (function): The function to test the CSV data.

    Returns:
        bool: True if it is a CSV file of the specified type, False otherwise.
    """
    result = False

    if os.path.getsize(file_path) < max_size and os.path.isfile(file_path):
        try:
            with open(file_path, encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                result = test_func(csv_reader)
        except UnicodeDecodeError:
            return result
        except IsADirectoryError:
            return result
        except csv.Error:
            return result

    return result


def get_view_urls(metadata_file):
    """
    Get the view URLs from the metadata file.

    Args:
        metadata_file (str): The path to the metadata file.

    Returns:
        list: A list of view URLs.
    """
    view_urls = []

    try:
        with open(metadata_file, encoding='utf-8') as f:
            file_data = f.read()

        json_data = json.loads(file_data)

        if json_data:
            if isinstance(json_data, list):
                for entry in json_data:
                    if 'URL' in entry and 'Type' in entry:
                        entry_type = entry['Type']
                        if entry_type.lower() == "view":
                            view_url = os.path.join(os.path.dirname(metadata_file), entry['URL'])
                            view_urls.append(view_url)

    except json.decoder.JSONDecodeError:
        return view_urls

    return view_urls


def search_for_metadata_files(dataset_dir, max_size):
    """
    Search for metadata files in the dataset directory.

    Args:
        dataset_dir (str): The dataset directory path.
        max_size (int): The maximum allowed file size.

    Returns:
        tuple: A tuple containing a list of metadata file paths and a dictionary mapping metadata file paths to view URLs.
    """
    metadata = []
    metadata_views = {}
    result = list(Path(dataset_dir).rglob("*"))

    for r in result:
        meta = is_json_of_type(r, max_size, contains_metadata)

        if meta:
            metadata.append(str(r))
            view_urls = get_view_urls(str(r))
            metadata_views[str(r)] = view_urls

    return metadata, metadata_views


def search_for_image_files(dataset_dir):
    """
    Search for thumbnail files in the dataset directory that correspond to the given view files.

    Args:
        dataset_dir (str): The dataset directory path.

    Returns:
        list: A list of thumbnail file paths.
    """
    image_file_paths = list(Path(dataset_dir).rglob("*.png"))
    image_file_paths += list(Path(dataset_dir).rglob("*.jpeg"))
    image_file_paths += list(Path(dataset_dir).rglob("*.jpg"))
    image_file_paths = list(set(image_file_paths))

    return image_file_paths


def _add_file(mime_type_list, potential_file, thumbnail_file):
    common_path = os.path.commonprefix([potential_file, thumbnail_file])
    if not os.path.isdir(common_path):
        common_prefix = os.path.basename(common_path)
        thumbnail_file_name = os.path.basename(thumbnail_file)
        potential_file_name = os.path.basename(potential_file)
        if thumbnail_file_name.startswith(common_prefix) and potential_file_name.startswith(common_prefix):
            mime_type_list.append(potential_file)


def _filter_alt_forms_by_thumbnail(thumbnail_files):
    alt_forms_files = {
        STL_MODEL_MIME: [],
        VTK_MODEL_MIME: [],
    }
    for thumbnail_file in thumbnail_files:
        target_dir = os.path.dirname(thumbnail_file)
        files = os.listdir(os.path.dirname(thumbnail_file))
        for f in files:
            potential_file = os.path.join(target_dir, f)
            if os.path.isfile(potential_file) and potential_file is not thumbnail_file:
                if potential_file.endswith(".vtk"):
                    _add_file(alt_forms_files[VTK_MODEL_MIME], potential_file, thumbnail_file)
                if potential_file.endswith(".stl"):
                    _add_file(alt_forms_files[STL_MODEL_MIME], potential_file, thumbnail_file)

    return alt_forms_files


def filter_thumbnail_files_by_parent(image_file_paths, parent_files):
    """
    Filter a list of image file paths to include only those whose in the same folder
    of any parent file in the given parent_files.

    Args:
        image_file_paths (list): List of image file paths.
        parent_files (list): List of parent files paths.

    Returns:
        list: Filtered list of image file paths.
    """
    filtered_files = []

    for parent_file in parent_files:
        parent_dir = os.path.dirname(parent_file)
        filtered_files.extend(
            [image_file for image_file in image_file_paths if os.path.dirname(image_file) == parent_dir]
        )

    return list(set(filtered_files))


def search_for_view_files(dataset_dir, max_size):
    """
    Search for view files in the dataset directory.

    Args:
        dataset_dir (str): The dataset directory path.
        max_size (int): The maximum allowed file size.

    Returns:
        list: A list of view file paths.
    """
    metadata = []
    result = list(Path(dataset_dir).rglob("*.json"))

    for r in result:
        meta = is_json_of_type(r, max_size, represents_view)
        if meta:
            metadata.append(str(r))

    return metadata


def search_for_plot_files(dataset_dir):
    """
    Search for plot files in the dataset directory.

    Args:
        dataset_dir (str): The dataset directory path.

    Returns:
        list: A list containing CSV and TSV plot file paths.
    """
    plot_files = []
    csv_files = list(Path(dataset_dir).rglob("*csv"))
    plot_files += csv_files

    tsv_files = list(Path(dataset_dir).rglob("*tsv"))
    plot_files += tsv_files

    txt_files = list(Path(dataset_dir).rglob("*txt"))
    for txt_file in txt_files:
        if generate_dataframe_from_txt(txt_file) is not None:
            plot_files.append(txt_file)

    return plot_files


def search_for_context_data_files(dataset_dir, max_size):
    context_data_files = []
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        _is_context_data_file = is_json_of_type(r, max_size, is_context_data_file)
        if _is_context_data_file:
            context_data_files.append(r)

    return context_data_files


class OnDiskFiles(metaclass=Singleton):
    """
    Singleton class for managing on-disk files.

    This class provides methods for setting and retrieving metadata, view, thumbnail, alternative forms,
    and plot files from a dataset directory. It also provides a method for setting up the
    dataset by searching for the required files.

    Attributes:
        _plot_files (dict): Dictionary containing lists of CSV and TSV plot file paths.
        _scaffold_files (dict): Dictionary containing lists of metadata, view, and thumbnail file paths.
    """

    _dataset_dir = None
    _image_paths = []
    _plot_files = {
        'plot': [],
        'thumbnail': [],
    }
    _scaffold_files = {
        'metadata': [],
        'view': [],
        'thumbnail': [],
        'alt_forms': {},
    }
    _context_info_files = []

    def is_defined(self):
        return self._dataset_dir is not None

    def setup_dataset(self, dataset_dir, max_size):
        """
        Set up the dataset by searching for the required files.

        Args:
            dataset_dir (str): The dataset directory path.
            max_size (int): The maximum allowed file size.

        Returns:
            OnDiskFiles: The instance of the class.
        """
        self._dataset_dir = dataset_dir
        self._image_paths = search_for_image_files(dataset_dir)

        metadata_file, metadata_views = search_for_metadata_files(dataset_dir, max_size)
        self.set_metadata_files(metadata_file, metadata_views)

        self._scaffold_files["view"] = search_for_view_files(dataset_dir, max_size)
        self._scaffold_files["thumbnail"] = filter_thumbnail_files_by_parent(self._image_paths,
                                                                             self._scaffold_files["view"])
        self._scaffold_files["alt_forms"] = _filter_alt_forms_by_thumbnail(self._scaffold_files["thumbnail"])

        self._plot_files["plot"] = search_for_plot_files(self._dataset_dir)
        self._plot_files["thumbnail"] = filter_thumbnail_files_by_parent(self._image_paths,
                                                                         self._plot_files["plot"])

        self._context_info_files = search_for_context_data_files(self._dataset_dir, convert_to_bytes("2MiB"))

        return self

    def get_dataset_dir(self):
        return self._dataset_dir

    def set_metadata_files(self, files, metadata_views):
        """
        Set the metadata files and metadata views.

        Args:
            files (list): List of metadata file paths.
            metadata_views (dict): Dictionary containing metadata view file paths.
        """
        self._scaffold_files['metadata'] = files

    def get_metadata_files(self):
        """
        Get the metadata file paths.

        Returns:
            list: List of metadata file paths.
        """
        return [str(i) for i in self._scaffold_files['metadata']]

    def get_view_files(self):
        """
        Get the view file paths.

        Returns:
            list: List of view file paths.
        """
        return [str(i) for i in self._scaffold_files['view']]

    def get_alt_forms_files(self):
        """
        Get the alternative forms file paths.

        Returns:
            list: List of alternative forms file paths.
        """
        return self._scaffold_files['alt_forms']

    def get_thumbnail_files(self):
        """
        Get the thumbnail file paths.

        Returns:
            list: List of thumbnail file paths.
        """
        return [str(i) for i in self._scaffold_files['thumbnail']]

    def get_plot_files(self):
        """
        Get the plot file paths.

        Returns:
            list: Lists of CSV and TSV plot file paths.
        """
        return [str(i) for i in self._plot_files['plot']]

    def get_plot_thumbnails(self):
        """
        Get the plot thumbnail paths.

        Returns:
            list: Lists of plot thumbnail paths.
        """
        return [str(i) for i in self._plot_files['thumbnail']]

    def get_all_image_files(self):
        """
        Get all the image file paths.

        Returns:
            list: List of all image file paths.
        """
        return [str(i) for i in self._image_paths]

    def get_context_info_files(self):
        return [str(i) for i in self._context_info_files]

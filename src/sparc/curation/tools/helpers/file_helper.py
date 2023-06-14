import csv
import json
import os
from pathlib import Path

from sparc.curation.tools.helpers.base import Singleton


ZINC_GRAPHICS_TYPES = ["points", "lines", "surfaces", "contours", "streamlines"]


def _is_graphics_entry(entry):
    """
    Check if the given entry is a graphics entry.

    Args:
        entry (dict): The entry to check.

    Returns:
        bool: True if it is a graphics entry, False otherwise.
    """
    if 'URL' in entry and 'Type' in entry:
        entry_type = entry['Type']
        if entry_type.lower() in ZINC_GRAPHICS_TYPES:
            return True

    return False


def _is_view_entry(entry):
    """
    Check if the given entry is a view entry.

    Args:
        entry (dict): The entry to check.

    Returns:
        bool: True if it is a view entry, False otherwise.
    """
    if 'URL' in entry and 'Type' in entry:
        entry_type = entry['Type']
        if entry_type.lower() == "view":
            return True

    return False


def test_for_metadata(json_data):
    """
    Test if the given JSON data contains metadata.

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
                if not have_viewable_graphics and _is_graphics_entry(entry):
                    have_viewable_graphics = True
                if not have_view_reference and _is_view_entry(entry):
                    have_view_reference = True

    return have_view_reference and have_viewable_graphics


def test_for_view(json_data):
    """
    Test if the given JSON data represents a view.

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
            # "version" and "id" are required keys for a context data file.
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
        meta = is_json_of_type(r, max_size, test_for_metadata)

        if meta:
            metadata.append(str(r))
            view_urls = get_view_urls(str(r))
            metadata_views[str(r)] = view_urls

    return metadata, metadata_views


def search_for_thumbnail_files(dataset_dir, view_files):
    """
    Search for thumbnail files in the dataset directory that correspond to the given view files.

    Args:
        dataset_dir (str): The dataset directory path.
        view_files (list): A list of view file paths.

    Returns:
        list: A list of thumbnail file paths.
    """
    potential_thumbnails = list(Path(dataset_dir).rglob("*thumbnail*"))
    potential_thumbnails += list(Path(dataset_dir).rglob("*.png"))
    potential_thumbnails += list(Path(dataset_dir).rglob("*.jpeg"))
    potential_thumbnails += list(Path(dataset_dir).rglob("*.jpg"))
    potential_thumbnails = list(set(potential_thumbnails))

    result = []
    for view_file in view_files:
        view_dir = os.path.dirname(view_file)
        result.extend([image_file for image_file in potential_thumbnails if view_dir == os.path.dirname(image_file)])

    result = list(set(result))
    # For each result:
    #   - Is this file actually an image?
    # Probably just leave this for now and go with the simple name comparison.
    return [str(x) for x in result]


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
    result = list(Path(dataset_dir).rglob("*"))
    for r in result:
        meta = is_json_of_type(r, max_size, test_for_view)

        if meta:
            metadata.append(str(r))

    return metadata


def search_for_plot_files(dataset_dir):
    """
    Search for plot files in the dataset directory.

    Args:
        dataset_dir (str): The dataset directory path.

    Returns:
        dict: A dictionary containing lists of CSV and TSV plot file paths.
    """
    plot_files = []
    csv_files = list(Path(os.path.join(dataset_dir, "primary")).rglob("*csv"))
    plot_files += csv_files

    tsv_files = list(Path(os.path.join(dataset_dir, "primary")).rglob("*tsv"))
    plot_files += tsv_files

    txt_files = list(Path(os.path.join(dataset_dir, "primary")).rglob("*txt"))
    for r in txt_files:
        csv_location = create_csv_from_txt(r)
        plot_files.append(csv_location)

    return plot_files


def create_csv_from_txt(file_path):
    """
    Create a CSV file from a text file.

    Args:
        file_path (str): The path to the text file.

    Returns:
        str: The path to the created CSV file.
    """
    data = open(file_path)
    start = False
    finish = False
    csv_rows = []
    for line in data:
        if "+Fin" in line:
            finish = True
        elif start and not finish:
            line_data_list = line.split()
            if line_data_list[1].startswith("D"):
                clean_data = line_data_list[1][1:].split(",")
                line_data_list.pop()
                if line_data_list[0].endswith("s"):
                    line_data_list[0] = line_data_list[0][:-1]
                line_data_list += clean_data
                csv_rows.append(line_data_list)
        else:
            if "EIT STARTING" in line:
                start = True
    file_path = os.path.splitext(file_path)[0]
    csv_file_name = f"{file_path}.csv"
    with open(csv_file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Time', 'V'])
        writer.writerows(csv_rows)

    return csv_file_name


class OnDiskFiles(metaclass=Singleton):
    """
    Singleton class for managing on-disk files.

    This class provides methods for setting and retrieving metadata, view, thumbnail, and plot files from a dataset directory.
    It also provides a method for setting up the dataset by searching for the required files.

    Attributes:
        _plot_files (dict): Dictionary containing lists of CSV and TSV plot file paths.
        _scaffold_files (dict): Dictionary containing lists of metadata, view, and thumbnail file paths.

    Methods:
        setup_dataset(dataset_dir, max_size): Set up the dataset by searching for the required files.
        set_metadata_files(files, metadata_views): Set the metadata files and metadata views.
        get_metadata_files(): Get the metadata file paths.
        set_view_files(files): Set the view files.
        get_view_files(): Get the view file paths.
        set_thumbnail_files(files): Set the thumbnail files.
        get_thumbnail_files(): Get the thumbnail file paths.
        get_plot_files(): Get the plot file paths.
    """

    _dataset_dir = None
    _plot_files = []
    _scaffold_files = {
        'metadata': [],
        'view': [],
        'thumbnail': [],
    }

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
        scaffold_files_dir = os.path.join(self._dataset_dir, "derivative")
        metadata_file, metadata_views = search_for_metadata_files(scaffold_files_dir, max_size)
        self.set_metadata_files(metadata_file, metadata_views)
        self.set_view_files(search_for_view_files(scaffold_files_dir, max_size))
        self.set_thumbnail_files(search_for_thumbnail_files(scaffold_files_dir, self.get_view_files()))
        self._plot_files = search_for_plot_files(self._dataset_dir)
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
        return self._scaffold_files['metadata']

    def set_view_files(self, files):
        """
        Set the view files.

        Args:
            files (list): List of view file paths.
        """
        self._scaffold_files['view'] = files

    def get_view_files(self):
        """
        Get the view file paths.

        Returns:
            list: List of view file paths.
        """
        return self._scaffold_files['view']

    def set_thumbnail_files(self, files):
        """
        Set the thumbnail files.

        Args:
            files (list): List of thumbnail file paths.
        """
        self._scaffold_files['thumbnail'] = files

    def get_thumbnail_files(self):
        """
        Get the thumbnail file paths.

        Returns:
            list: List of thumbnail file paths.
        """
        return self._scaffold_files['thumbnail']

    def get_plot_files(self):
        """
        Get the plot file paths.

        Returns:
            list: Lists of CSV and TSV plot file paths.
        """
        return self._plot_files

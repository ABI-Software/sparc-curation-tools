import os
import re
import argparse
import json

from sparc.curation.tools.definitions import FILE_LOCATION_COLUMN
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.utilities import convert_to_bytes

import sparc.curation.tools.plot_utilities as plot_utilities

VERSION = '1.2.0'
AVAILABLE_PLOT_TYPES = ['heatmap', 'timeseries']
AVAILABLE_DELIMITERS = ['tab', 'comma']


def parse_num_list(string):
    m = re.match(r'^(\d+)(?:-(\d+))?$', string)
    if not m:
        raise argparse.ArgumentTypeError("'" + string + "' is not a range of numbers. Expected forms like '0-5'.")
    start = m.group(1)
    end = m.group(2) or start
    return list(range(int(start, 10), int(end, 10) + 1))


def flatten_nested_list(nested_list):
    flat_list = []
    # Iterate over all the elements in given list
    for elem in nested_list:
        # Check if type of element is list
        if isinstance(elem, list):
            # Extend the flat list by adding contents of this element (list)
            flat_list.extend(flatten_nested_list(elem))
        else:
            # Append the element to the list
            flat_list.append(elem)
    return flat_list


def annotate_plot_from_plot_paths(plot_paths):
    for plot_path in plot_paths:
        plot = plot_utilities.create_plot_from_plot_path(plot_path)
        if plot:
            annotate_one_plot(plot)


def annotate_one_plot(plot):
    plot_utilities.generate_plot_thumbnail(plot)
    data = get_plot_annotation_data(plot)
    ManifestDataFrame().update_plot_annotation(plot.location, data, plot.thumbnail)


def get_all_plots_path():
    return OnDiskFiles().get_plot_files()


def get_all_plots():
    plot_files = OnDiskFiles().get_plot_files()
    plot_path_list = []
    plot_list = []
    for plot_file in plot_files:
        plot = get_plot_from_path(plot_file)
        if plot:
            plot_path_list.append(plot_file)
            plot_list.append(plot)
    return plot_path_list, plot_list


def get_plot_from_path(plot_path):
    return plot_utilities.create_plot_from_plot_path(plot_path)


def get_plot_thumbnails():
    return OnDiskFiles().get_plot_thumbnails()


def get_filename_by_location(object_text):
    ManifestDataFrame().get_matching_entry(FILE_LOCATION_COLUMN, object_text)


def update_column_content(subject_text, predicate_text, object_value, append):
    ManifestDataFrame().update_column_content(subject_text, predicate_text, object_value, append)


def get_annotated_plot_dictionary():
    """
    Build and return a plot dictionary based on plot annotation in manifest files.
    The annotated plot dictionary has the following structure:
    {
        plot_file: [thumbnail_files]
    }

    Returns:
        dict: Plot dictionary.
    """
    manifest = ManifestDataFrame()
    annotated_plot_dictionary = {}

    # Get a list of plot files in the manifest
    plot_files = manifest.scaffold_get_plot_files()

    for plot_file in plot_files:
        # Get the directory where the metadata file is located
        manifest_dir = manifest.get_manifest_directory(plot_file)[0]

        # Get a list of thumbnail filenames associated with the plot_file
        thumbnail_filenames = manifest.get_source_of(plot_file)

        # Create a list to store thumbnail information for this view
        plot_entry = [os.path.join(manifest_dir, thumbnail) for thumbnail in thumbnail_filenames
                      if not isinstance(thumbnail, float)]

        # Add the metadata entry to the annotated scaffold dictionary
        annotated_plot_dictionary[plot_file] = plot_entry

    return annotated_plot_dictionary


def get_plot_annotation_data(plot_file):
    attrs = {
        'style': plot_file.plot_type,
    }
    if plot_file.x_axis_column != 0:
        attrs['x-axis'] = plot_file.x_axis_column

    if plot_file.delimiter != 'comma':
        attrs['delimiter'] = plot_file.delimiter

    if len(plot_file.y_axes_columns):
        attrs['y-axes-columns'] = flatten_nested_list(plot_file.y_axes_columns)

    if plot_file.no_header:
        attrs['no-header'] = plot_file.no_header

    if plot_file.row_major:
        attrs['row-major'] = plot_file.row_major

    data = {
        'version': VERSION,
        'type': 'plot',
        'attrs': attrs
    }
    return json.dumps(data)


def get_confirmation_message(error=None):
    """
    "To fix this error, the 'additional types' of 'filename' in 'manifestFile' will be set to 'MIME'."
    "To fix this error, a manifestFile will be created under manifestDir, and will insert the filename in this manifestFile with 'additional types' MIME."

    "To fix this error, the data of filename in manifestFile will be deleted."
    """
    if error is None:
        return "Let this magic tool annotate all plots for you?"

    return "Let this magic tool annotate this plot for you?"


def main():
    parser = argparse.ArgumentParser(description='Create an annotation for a SPARC plot. '
                                                 'The Y_AXES_COLUMNS can either be single numbers or a range in the form 5-8. '
                                                 'The start and end numbers are included in the range. '
                                                 'The -y/--y-axes-columns argument will consume the positional plot type argument. '
                                                 'That means the positional argument cannot follow the -y/--y-axes-columns.')
    parser.add_argument("dataset_dir", help='dataset dir')
    parser.add_argument("-plot_type", "--plot_type",
                        help='must define a plot type which is one of; ' + ', '.join(AVAILABLE_PLOT_TYPES) + '.',
                        choices=AVAILABLE_PLOT_TYPES, default="timeseries")
    parser.add_argument("-x", "--x-axis-column",
                        help="integer index for the independent column (zero based). Default is 0.",
                        type=int, default=0)
    parser.add_argument("-y", "--y-axes-columns",
                        help="list of indices for the dependent columns (zero based). Can be used multiple times."
                             " Can be specified as a range e.g. 5-8. Default is [].",
                        default=[], nargs='*', action="append", type=parse_num_list)
    parser.add_argument("-n", "--no-header",
                        help="Boolean to indicate whether a header line is missing. Default is False.",
                        action="store_true", default=False)
    parser.add_argument("-r", "--row-major",
                        help="Boolean to indicate whether the data is row major or column major. Default is False.",
                        action="store_true", default=False)
    parser.add_argument("-d", "--delimiter", help="The type of delimiter used, must be one of; " + ", ".join(
        AVAILABLE_DELIMITERS) + ". Default is comma.",
                        default='comma', choices=AVAILABLE_DELIMITERS)

    args = parser.parse_args()
    dataset_dir = args.dataset_dir
    max_size = convert_to_bytes('3000MiB')
    OnDiskFiles().setup_dataset(dataset_dir, max_size)
    ManifestDataFrame().setup_dataframe(dataset_dir)
    annotate_plot_from_plot_paths(get_all_plots_path())


if __name__ == "__main__":
    main()

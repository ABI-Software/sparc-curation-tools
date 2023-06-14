import os
import re
import argparse
import json

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


def annotate_all_plot(dataset_dir, data=None):
    max_size = '2000MiB'
    OnDiskFiles().setup_dataset(dataset_dir, convert_to_bytes(max_size))
    ManifestDataFrame().setup_dataframe(dataset_dir)

    if data:
        pass
        # TODO For script call the annotate all plot method directly
        # ManifestDataFrame().update_plot_annotation(manifest_dir, plot_file.location, data, plot_file.thumbnail)
    else:
        # Check if the plot is already annotated first.
        annotate_plot_from_plot_paths(OnDiskFiles().get_plot_files())


def annotate_plot_from_plot_paths(plot_paths):
    plot_list = plot_utilities.create_plots_list_from_plot_paths(plot_paths)
    plot_utilities.generate_plot_thumbnail(plot_list)
    manifest_dir = os.path.join(OnDiskFiles().get_dataset_dir(), "primary")

    for plot_file in plot_list:
        data = get_plot_annotation_data(plot_file)
        ManifestDataFrame().update_plot_annotation(manifest_dir, plot_file.location, data, plot_file.thumbnail)


def get_all_plots_path():
    return OnDiskFiles().get_plot_files()


def get_all_thumbnail_path():
    return OnDiskFiles().get_thumbnail_files()


def get_manifest():
    return ManifestDataFrame()


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


def get_path_by_name(file_name):
    return ManifestDataFrame().get_filepath_on_disk(file_name)

def get_confirmation_message(error=None):
    """
    "To fix this error, the 'additional types' of 'filename' in 'manifestFile' will be set to 'MIME'."
    "To fix this error, a manifestFile will be created under manifestDir, and will insert the filename in this manifestFile with 'additional types' MIME."

    "To fix this error, the data of filename in manifestFile will be deleted."
    """
    if error is None:
        return "Let this magic tool annotation plots for you?"

    message = "Let this magic tool annotation this plot for you?"
    return message


def main():
    parser = argparse.ArgumentParser(description='Create an annotation for a SPARC plot. '
                                                 'The Y_AXES_COLUMNS can either be single numbers or a range in the form 5-8. '
                                                 'The start and end numbers are included in the range. '
                                                 'The -y/--y-axes-columns argument will consume the positional plot type argument. '
                                                 'That means the positional argument cannot follow the -y/--y-axes-columns.')
    parser.add_argument("dataset_dir", help='dataset dir')
    parser.add_argument("-plot_type","--plot_type", help='must define a plot type which is one of; ' + ', '.join(AVAILABLE_PLOT_TYPES) + '.',
                        choices=AVAILABLE_PLOT_TYPES, default="timeseries")
    parser.add_argument("-x", "--x-axis-column", help="integer index for the independent column (zero based). Default is 0.",
                        type=int, default=0)
    parser.add_argument("-y", "--y-axes-columns", help="list of indices for the dependent columns (zero based). Can be used multiple times."
                                                       " Can be specified as a range e.g. 5-8. Default is [].",
                        default=[], nargs='*', action="append", type=parse_num_list)
    parser.add_argument("-n", "--no-header", help="Boolean to indicate whether a header line is missing. Default is False.",
                        action="store_true", default=False)
    parser.add_argument("-r", "--row-major", help="Boolean to indicate whether the data is row major or column major. Default is False.",
                        action="store_true", default=False)
    parser.add_argument("-d", "--delimiter", help="The type of delimiter used, must be one of; " + ", ".join(AVAILABLE_DELIMITERS) + ". Default is comma.",
                        default='comma', choices=AVAILABLE_DELIMITERS)

    args = parser.parse_args()
    dataset_dir = args.dataset_dir
    
    #TODO
    data = get_plot_annotation_data(args)
    annotate_all_plot(dataset_dir, json.dumps(data))


if __name__ == "__main__":
    main()

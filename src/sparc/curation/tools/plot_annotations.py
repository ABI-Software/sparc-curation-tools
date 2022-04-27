import os
import re
import argparse
import json

from sparc.curation.tools.manifests import ManifestDataFrame
from sparc.curation.tools.ondisk import OnDiskFiles
from sparc.curation.tools.utilities import convert_to_bytes

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

def annotate_plot(dataset_dir, data):
    max_size = '2000MiB'
    manifest_dir = os.path.join(dataset_dir, "primary")
    OnDiskFiles().setup_dataset(dataset_dir, convert_to_bytes(max_size))
    ManifestDataFrame().setup_dataframe(dataset_dir)
    plot_files = OnDiskFiles().get_plot_files()
    for plot_file in plot_files:
        data = get_plot_annotation_data(plot_file)
        ManifestDataFrame().update_plot_annotation(manifest_dir, plot_file.location, data, plot_file.thumbnail)

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
    annotate_plot(dataset_dir, json.dumps(data))


main()

import os
import plotly.express as px
import pandas as pd

from sparc.curation.tools.models.plot import Plot


def create_plot_from_plot_path(file_path):
    if file_path.endswith('.csv'):
        plot_df = pd.read_csv(file_path, header=None)
        plot = Plot(file_path, plot_df)
        return get_plot(plot, plot_df)
    elif file_path.endswith('.tsv'):
        plot_df = pd.read_csv(file_path, header=None, sep='\t')
        plot = Plot(file_path, plot_df, delimiter="tab")
        return get_plot(plot, plot_df)
    elif file_path.endswith('.txt'):
        plot_df = generate_dataframe_from_txt(file_path)
        plot = Plot(file_path, plot_df, delimiter="tab")
        return get_plot(plot, plot_df)


def generate_dataframe_from_txt(file_path):
    """
    Generate a dataframe from a text file.

    Args:
        file_path (str): The path to the text file.

    Returns:
        dataframe: The dataframe generated from the txt file.
    """
    start = False
    finish = False
    csv_rows = []

    with open(file_path) as f:
        for line in f:
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

    if csv_rows:
        df = pd.DataFrame(csv_rows)
    else:
        df = pd.read_csv(file_path, header=None, delimiter='\t', low_memory=False)

    if is_valid_plot(df):
        return df


def get_plot(plot, plot_df):
    # if plot_df only has one cell or has null, not valid
    if plot_df is None or plot_df.empty or plot_df.size == 1:
        return None

    first_row = plot_df.iloc[0]
    are_all_floats_or_ints = first_row.apply(lambda x: isinstance(x, (float, int))).all()
    # if plot_df first row all floats or ints, no header
    if are_all_floats_or_ints:
        plot.set_has_header(False)
    else:
        plot_df.columns = plot_df.iloc[0].astype(str)
        plot_df = plot_df.drop(0)
        plot.plot_df = plot_df
        plot.set_has_header(True)
        # Convert column names to lowercase
        plot_df.columns = plot_df.columns.str.lower()

    if plot.has_header():
        time_column = next((col for col in plot_df.columns if 'time' in col.lower()), None)
        if time_column and is_unique_increasing(plot_df[time_column]):
            plot.x_axis_column = plot_df.columns.get_loc(time_column)
            plot.plot_type = 'timeseries'
        else:
            plot.plot_type = 'heatmap'
    else:
        x_column = next((col for col in plot_df.columns if is_unique_increasing(plot_df[col])), None)
        if x_column is not None:
            plot.x_axis_column = x_column
            plot.plot_type = 'timeseries'
        else:
            plot.plot_type = 'heatmap'
    # Return the selected plot object
    return plot


def is_unique_increasing(series):
    try:
        series = series.astype(float)
    except ValueError:
        return False
    return series.is_monotonic_increasing and series.is_unique


def is_valid_plot(df):

    has_valid_shape = df.shape[0] > 1 and df.shape[1] > 1

    same_data_count_per_row = df.apply(lambda row: len(row) == len(df.columns), axis=1).all()

    is_valid_data = has_valid_shape and same_data_count_per_row

    return is_valid_data


def create_thumbnail_from_plot(plot):
    fig = None
    if plot.plot_type == "timeseries":
        fig = px.scatter(plot.plot_df, x=plot.get_x_column_name(), y=plot.get_y_columns_name())
    elif plot.plot_type == "heatmap":
        fig = px.imshow(plot.plot_df, y=plot.get_y_columns_name(), aspect="auto")

    if fig:
        fig_path = os.path.splitext(plot.location)[0]
        fig_name = fig_path + '.jpg'
        fig.write_image(fig_name)
        plot.set_thumbnail(os.path.join(os.path.dirname(plot.location), fig_name))


def generate_plot_thumbnail(plot):
    if px is None:
        print("Plotly is not available, install for thumbnail generating functionality.")
    else:
        create_thumbnail_from_plot(plot)

import os
import plotly.express as px
import pandas as pd

from sparc.curation.tools.models.plot import Plot


def create_plots_list_from_plot_paths(plot_paths):
    plot_list = []
    for file_path in plot_paths:
        if file_path.endswith('.csv'):
            plot_list.append(get_plot(file_path))
        elif file_path.endswith('.tsv'):
            plot_list.append(get_plot(file_path, is_tsv=True))

    return plot_list


def get_plot(csv_file, is_tsv=False):
    if is_tsv:
        plot_df = pd.read_csv(csv_file, sep='\t')
    else:
        plot_df = pd.read_csv(csv_file)
    plot_df.columns = plot_df.columns.str.lower()
    plot = None
    x_loc = 0
    y_loc = []
    if "time" in plot_df.columns:
        if plot_df["time"].is_monotonic_increasing and plot_df["time"].is_unique:
            x_loc = plot_df.columns.get_loc("time")
            if x_loc != 0:
                y_loc = list(range(x_loc + 1, len(plot_df.columns)))
            plot = Plot(csv_file, "timeseries", x=x_loc, y=y_loc)
        else:
            plot = Plot(csv_file, "heatmap")
    else:
        if is_tsv:
            plot_df = pd.read_csv(csv_file, header=None, sep='\t')
        else:
            plot_df = pd.read_csv(csv_file, header=None)
        for column in plot_df.columns[:3]:
            if plot_df[column].is_monotonic_increasing and plot_df[column].is_unique:
                if x_loc != 0:
                    y_loc = list(range(x_loc + 1, len(plot_df.columns)))
                plot = Plot(csv_file, "timeseries", delimiter = "tab", x=x_loc, y=y_loc, no_header=True)
                break
            x_loc += 1
        if not plot:
            plot = Plot(csv_file, "heatmap", no_header=True)
    return plot


def create_thumbnail_from_plot(plot, plot_df):
    fig = None
    if plot.plot_type == "timeseries" and not plot.no_header:
        fig = px.scatter(plot_df, x="time", y=plot_df.columns[plot.x_axis_column + 1:])
    elif plot.plot_type == "heatmap" and not plot.no_header:
        fig = px.imshow(plot_df)
    elif plot.plot_type == "timeseries" and plot.no_header:
        fig = px.scatter(plot_df, x=plot_df.columns[plot.x_axis_column], y=plot_df.columns[plot.x_axis_column + 1:])
    elif plot.plot_type == "heatmap" and plot.no_header:
        fig = px.imshow(plot_df, x=plot_df.iloc[0], y=plot_df[0])

    if fig:
        fig_path = os.path.splitext(plot.location)[0]
        fig_name = fig_path + '.jpg'
        fig.write_image(fig_name)
        plot.set_thumbnail(os.path.join(os.path.dirname(plot.location), fig_name))


def generate_plot_thumbnail(plot_files):
    for plot in plot_files:
        plot_df = None
        if plot.location.endswith(".tsv") and not plot.no_header:
            plot_df = pd.read_csv(plot.location, sep='\t')
            plot_df.columns = plot_df.columns.str.lower()
        elif plot.location.endswith(".csv") and not plot.no_header:
            plot_df = pd.read_csv(plot.location)
            plot_df.columns = plot_df.columns.str.lower()
        elif plot.location.endswith(".tsv") and plot.no_header:
            plot_df = pd.read_csv(plot.location, header=None, sep='\t')
        elif plot.location.endswith(".csv") and plot.no_header:
            plot_df = pd.read_csv(plot.location, header=None)

        if px is None:
            print("Plotly is not available, install for thumbnail generating functionality.")
        else:
            create_thumbnail_from_plot(plot, plot_df)

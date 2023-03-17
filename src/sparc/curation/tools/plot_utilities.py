import os
import plotly.express as px


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

class Plot(object):
    def __init__(self, location, plot_df, plot_type="invalid", no_header=True, delimiter='comma', x=0, y=None,
                 row_major=False,
                 thumbnail=None):
        self.location = location
        self.plot_type = plot_type
        self.plot_df = plot_df
        self.x_axis_column = x
        self.delimiter = delimiter
        self.y_axes_columns = [] if y is None else y
        self.no_header = no_header
        self.row_major = row_major
        self.thumbnail = thumbnail

    def set_thumbnail(self, thumbnail):
        self.thumbnail = thumbnail

    def set_has_header(self, has_header):
        self.no_header = not has_header

    def has_header(self):
        return not self.no_header

    def get_x_column_name(self):
        return self.plot_df.columns[self.x_axis_column]

    def set_y_columns(self, y_columns):
        max_index = len(self.plot_df.columns) - 1
        self.y_axes_columns = [index for index in y_columns if 0 <= index <= max_index]

    def get_y_columns_name(self):
        if self.y_axes_columns:
            return self.plot_df.columns[self.y_axes_columns]
        return self.plot_df.columns[self.x_axis_column + 1:]
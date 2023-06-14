class Plot(object):
    def __init__(self, location, plot_type, no_header=False, delimiter='comma', x=0, y=None, row_major=False,
                 thumbnail=None):
        self.location = location
        self.plot_type = plot_type
        self.x_axis_column = x
        self.delimiter = delimiter
        self.y_axes_columns = [] if y is None else y
        self.no_header = no_header
        self.row_major = row_major
        self.thumbnail = thumbnail

    def set_thumbnail(self, thumbnail):
        self.thumbnail = thumbnail

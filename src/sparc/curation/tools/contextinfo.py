

class ContextInfoAnnotation(object):

    _version = "0.2.0"

    def __init__(self, metadata_file, filename):
        self._metadata_file = metadata_file
        self._filename = filename
        self._context_heading = ""
        self._banner = ""
        self._context_description = ""
        self._samples = []
        self._views = []

    def __str__(self):
        v_str = ''
        for v in self._views:
            v_str += "\n" + str(v)
        s_str = ''
        for s in self._samples:
            s_str += "\n" + str(s)
        return f"""version: {self._version}
heading: {self._context_heading}
banner: {self._banner}
#samples: {len(self._samples)}
{s_str}
#views: {len(self._views)}
{v_str}
"""

    def from_dict(self, data):
        self._metadata_file = data["metadata"] if "metadata" in data else ""
        self._context_heading = data["heading"] if "heading" in data else ""
        self._banner = data["banner"] if "banner" in data else ""
        self._context_description = data["description"] if "description" in data else ""
        self._samples = data["samples"] if "samples" in data else []
        self._views = data["views"] if "views" in data else []

    def update(self, data):
        self._metadata_file = data["metadata"] if "metadata" in data else self._metadata_file
        self._context_heading = data["heading"] if "heading" in data else self._context_heading
        self._banner = data["banner"] if "banner" in data else self._banner
        self._context_description = data["description"] if "description" in data else self._context_description
        self._samples = data["samples"] if "samples" in data else self._samples
        self._views = data["views"] if "views" in data else self._views

    def as_dict(self):
        data = {
            "version": self._version,
            "id": "sparc.science.context_data",
            "metadata": self._metadata_file,
            "heading": self._context_heading,
            "banner": self._banner,
            "description": self._context_description,
            "samples": self._samples,
            "views": self._views,
        }
        return data

    def get_metadata_file(self):
        return self._metadata_file

    def get_filename(self):
        return self._filename

    def get_version(self):
        return self._version

    def get_banner(self):
        return self._banner

    def get_description(self):
        return self._context_description

    def get_heading(self):
        return self._context_heading

    def get_views(self):
        return self._views

    def get_samples(self):
        return self._samples

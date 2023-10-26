import json
import os
import unittest

import pandas as pd

from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.models.plot import Plot
from sparc.curation.tools.plot_annotations import get_all_plots_path, annotate_plot_from_plot_paths, get_plot_annotation_data, get_confirmation_message

from gitresources import dulwich_checkout, dulwich_clean, dulwich_proper_stash_and_drop, setup_resources
from sparc.curation.tools.utilities import convert_to_bytes

here = os.path.abspath(os.path.dirname(__file__))


class TestPlotAnnotations(unittest.TestCase):
    _repo = None

    @classmethod
    def setUpClass(cls):
        cls._repo = setup_resources()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._repo.close()

    def setUp(self):
        dulwich_checkout(self._repo, b"main")
        self._max_size = convert_to_bytes("2MiB")

    def tearDown(self):
        dulwich_proper_stash_and_drop(self._repo)

    def test_annotate_plot_from_plot_paths(self):
        print('(test_annotate_plot_from_plot_paths)', end='')
        dulwich_checkout(self._repo, b"origin/test_annotate_plot")

        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)

        manifest_file = os.path.join(here, 'resources', 'derivative', 'manifest.xlsx')
        expected_file = os.path.join(here, 'resources', 'derivative', 'manifest_expected.xlsx')
        manifest_data = pd.read_excel(manifest_file)
        expected_data = pd.read_excel(expected_file)

        self.assertFalse(expected_data.equals(manifest_data))

        plot_paths = get_all_plots_path()
        annotate_plot_from_plot_paths(plot_paths)
        manifest_data = pd.read_excel(manifest_file)

        dulwich_clean(self._repo, self._repo.path)
        print('------------------------')
        print(expected_data.compare(manifest_data))
        self.assertTrue(expected_data.equals(manifest_data))

    def test_get_all_plots_path(self):
        print('(test_get_all_plots_path)', end='')
        dulwich_checkout(self._repo, b"origin/test_annotate_plot")

        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)

        plot_paths = get_all_plots_path()
        plot_files = ['stim_distal-colon_manometry.csv', 'stim_proximal-colon_manometry.csv',
                      'stim_transverse-colon_manometry.csv', 'sub-001_ses-001_P_log.txt', 'sub-002_ses-003_T_log.txt']
        expected_data = [os.path.join(here, "resources", 'derivative', f) for f in plot_files]

        self.assertEqual(set(plot_paths), set(expected_data))

    def test_get_plot_annotation_data(self):
        print('(test_get_plot_annotation_data)', end='')

        plot_file = Plot("plot.png", [], plot_type="heatmap", no_header=False)

        data = get_plot_annotation_data(plot_file)

        expected_data = {
            'version': '1.2.0',
            'type': 'plot',
            'attrs': {
                'style': 'heatmap'
            }
        }

        self.assertEqual(expected_data, json.loads(data))

    def test_get_confirmation_message(self):
        confirmation_message = get_confirmation_message(error=None)
        self.assertEqual(confirmation_message, "Let this magic tool annotate all plots for you?")

        error_message = get_confirmation_message(error="Some error")
        self.assertEqual(error_message, "Let this magic tool annotate this plot for you?")


if __name__ == '__main__':
    unittest.main()

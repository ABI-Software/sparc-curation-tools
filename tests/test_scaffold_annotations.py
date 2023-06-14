import os.path

import pandas
import tabulate
import unittest

from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.helpers.file_helper import OnDiskFiles
from sparc.curation.tools.scaffold_annotations import get_errors, fix_errors
from sparc.curation.tools.utilities import convert_to_bytes

from gitresources import dulwich_checkout, setup_resources, dulwich_proper_stash_and_drop

here = os.path.abspath(os.path.dirname(__file__))


class ScaffoldAnnotationTestCase(unittest.TestCase):

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

    def test_correct_annotations(self):
        dulwich_checkout(self._repo, b"origin/scaffold_annotations_correct")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()
        self.assertEqual(0, len(errors))

    def test_clear_deprecated_annotations(self):
        dulwich_checkout(self._repo, b"origin/no_banner_bad_old_scaffold_annotations")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()
        self.assertEqual(6, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

    def test_annotate_bare_scaffold(self):
        dulwich_checkout(self._repo, b"origin/no_banner_no_scaffold_annotations")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()
        self.assertEqual(3, len(errors))

        errors_fixed = fix_errors(errors)

        self.assertTrue(errors_fixed)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

    def test_annotate_bare_scaffold_new_layout(self):
        dulwich_checkout(self._repo, b"origin/no_banner_no_scaffold_annotations_II")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()

        self.assertEqual(2, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

    def test_annotate_bare_scaffold_multiple_views_thumbnails(self):
        dulwich_checkout(self._repo, b"origin/no_scaffold_annotations_multiple_views")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()

        self.assertEqual(3, len(errors))

        fix_errors(errors)

        xlsx_file = os.path.join(dataset_dir, 'derivative', 'manifest.xlsx')
        df = pandas.read_excel(xlsx_file)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))
        self.assertEqual('rat_brainstem_Layout1_view.json', df['filename'][1])
        self.assertEqual('rat_brainstem_Layout1_thumbnail.jpeg', df['isSourceOf'][1])
        self.assertEqual('rat_brainstem_Layout2_view.json', df['filename'][4])
        self.assertEqual('rat_brainstem_Layout2_thumbnail.jpeg', df['isSourceOf'][4])

    def test_annotate_bare_multiple_scaffolds(self):
        dulwich_checkout(self._repo, b"origin/no_scaffold_annotations_multiple_scaffolds")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()

        self.assertEqual(4, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

        for subj in ['subject-01', 'subject-02']:
            manifest_file = os.path.join(here, 'resources', 'derivative', subj, 'manifest.xlsx')
            self.assertTrue(os.path.isfile(manifest_file))
            os.remove(manifest_file)
            self.assertFalse(os.path.isfile(manifest_file))

    def test_annotate_scaffold_with_additional_images(self):
        dulwich_checkout(self._repo, b"origin/no_scaffold_annotations_extra_images")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()

        self.assertEqual(2, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

        manifest_file = os.path.join(here, 'resources', 'derivative', 'manifest.xlsx')

        self.assertTrue(os.path.isfile(manifest_file))
        os.remove(manifest_file)
        self.assertFalse(os.path.isfile(manifest_file))


def print_as_table(xlsx_file):
    df = pandas.read_excel(xlsx_file)

    headers = [table_header(header) for header in df.keys()]
    print(tabulate.tabulate(df, headers=headers, tablefmt='simple'))


def print_errors(errors):
    for i, e in enumerate(errors):
        print(i + 1, e.get_error_message())


def table_header(in_header):
    if in_header == 'timestamp':
        return 'ts'
    elif in_header == 'file type':
        return 'type'
    elif in_header.startswith('Unnamed'):
        return '*'

    return in_header


if __name__ == "__main__":
    unittest.main()

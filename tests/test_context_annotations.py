import json
import os.path

import unittest

import pandas as pd
from sparc.curation.tools import context_annotations
from sparc.curation.tools.context_annotations import annotate_context_info
from sparc.curation.tools.definitions import SOURCE_OF_COLUMN
from sparc.curation.tools.helpers.file_helper import OnDiskFiles, search_for_context_data_files
from sparc.curation.tools.helpers.manifest_helper import ManifestDataFrame
from sparc.curation.tools.models.contextinfo import ContextInfoAnnotation
from sparc.curation.tools.scaffold_annotations import get_errors, fix_errors
from sparc.curation.tools.utilities import convert_to_bytes

from gitresources import dulwich_checkout, setup_resources, dulwich_proper_stash_and_drop, dulwich_clean

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
        dulwich_clean(self._repo, self._repo.path)

    def test_context_info_annotations(self):
        dulwich_checkout(self._repo, b"origin/scaffold_annotations_correct")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.1.0", content["version"])
        self.assertEqual("Generic rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Generic rat brainstem scaffold")

    def test_context_info_bare_scaffold_new_layout(self):
        dulwich_checkout(self._repo, b"origin/no_banner_no_scaffold_annotations_II")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.1.0", content["version"])
        self.assertEqual("Generic rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Generic rat brainstem scaffold")

    def test_context_info_bare_scaffold_multiple_views_thumbnails(self):
        dulwich_checkout(self._repo, b"origin/no_scaffold_annotations_multiple_views")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.1.0", content["version"])
        self.assertEqual("Generic rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Generic rat brainstem scaffold", 2)

    def test_context_info_bare_multiple_scaffolds(self):
        dulwich_checkout(self._repo, b"origin/no_scaffold_annotations_multiple_scaffolds")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.1.0", content["version"])
        self.assertEqual("Generic rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Generic rat brainstem scaffold")

    def test_context_info_multiple_metadata(self):
        dulwich_checkout(self._repo, b"origin/context_annotation_multiple_metadata")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(2, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.1.0", content["version"])
        self.assertEqual("Distribution of 5-HT", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Distribution of 5-HT", 1, 1)

    def test_context_info_scaffold_with_additional_images(self):
        dulwich_checkout(self._repo, b"origin/no_scaffold_annotations_extra_images")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.1.0", content["version"])
        self.assertEqual("Generic rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Generic rat brainstem scaffold")

    def test_context_info_annotation(self):
        dulwich_checkout(self._repo, b"origin/context_annotations_no_scaffold_annotations")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.2.0", content["version"])
        self.assertEqual("Rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Rat brainstem scaffold", 2)

        OnDiskFiles().setup_dataset(dataset_dir, convert_to_bytes("2MiB"))
        ManifestDataFrame().setup_dataframe(dataset_dir)

        annotate_context_info(ci)

        manifest_file = os.path.join(here, 'resources', 'derivative', 'manifest.xlsx')
        expected_file = os.path.join(here, 'resources', 'derivative', 'manifest_expected.xlsx')
        manifest_data = pd.read_excel(manifest_file)
        expected_data = pd.read_excel(expected_file)

        self.assertTrue(expected_data.equals(manifest_data))

    def test_context_info_annotation_with_scaffold(self):
        dulwich_checkout(self._repo, b"origin/no_annotations_multiple_views_context_annotation")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.2.0", content["version"])
        self.assertEqual("Rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Rat brainstem scaffold", 2)

        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()
        self.assertEqual(3, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))
        annotate_context_info(ci)

        manifest_file = os.path.join(here, 'resources', 'derivative', 'manifest.xlsx')
        expected_file = os.path.join(here, 'resources', 'derivative', 'manifest_expected.xlsx')
        manifest_data = pd.read_excel(manifest_file)
        expected_data = pd.read_excel(expected_file)

        self.assertTrue(expected_data.equals(manifest_data))

    def test_context_info_annotation_with_scaffold_opposite_order(self):
        dulwich_checkout(self._repo, b"origin/no_annotations_multiple_views_context_annotation_opposite_order")
        dataset_dir = os.path.join(here, "resources")
        context_files = search_for_context_data_files(dataset_dir, convert_to_bytes("2MiB"))

        self.assertEqual(1, len(context_files))
        with open(context_files[0]) as f:
            content = json.load(f)

        self.assertEqual("0.2.0", content["version"])
        self.assertEqual("Rat brainstem scaffold", content["heading"])

        ci = ContextInfoAnnotation(os.path.basename(context_files[0]), context_files[0])
        self._compare_update(ci, content, "Rat brainstem scaffold", 2)

        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)

        annotate_context_info(ci)

        errors = get_errors()
        self.assertEqual(3, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

        manifest_file = os.path.join(here, 'resources', 'derivative', 'manifest.xlsx')
        expected_file = os.path.join(here, 'resources', 'derivative', 'manifest_expected.xlsx')
        manifest_data = pd.read_excel(manifest_file)
        expected_data = pd.read_excel(expected_file)

        self._compare_source_of_columns(expected_data[SOURCE_OF_COLUMN], manifest_data[SOURCE_OF_COLUMN])

    def _compare_source_of_columns(self, col_1, col_2):
        for index, entry in enumerate(col_1):
            if pd.isna(entry):
                self.assertTrue(pd.isna(col_2[index]))
            else:
                self.assertEqual(set(entry.split('\n')), set(col_2[index].split('\n')))

    def _compare_update(self, ci, content, heading='', views_len=0, samples_len=0):
        self.assertEqual("0.2.0", ci.get_version())
        self.assertEqual('', ci.get_heading())
        self.assertEqual(0, len(ci.get_views()))
        self.assertEqual(0, len(ci.get_samples()))

        ci.update(content)

        self.assertEqual("0.2.0", ci.get_version())
        self.assertEqual(heading, ci.get_heading())
        self.assertEqual(views_len, len(ci.get_views()))
        self.assertEqual(samples_len, len(ci.get_samples()))


def dump_json(files):
    for c in files:
        with open(c) as f:
            print(json.load(f))


if __name__ == "__main__":
    unittest.main()

import os.path
import unittest

import dulwich.porcelain
import dulwich.repo
from sparc.curation.tools.manifests import ManifestDataFrame
from sparc.curation.tools.ondisk import OnDiskFiles
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
        self.assertEqual(7, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))

    def test_annotate_bare_scaffold(self):
        dulwich_checkout(self._repo, b"origin/no_banner_no_scaffold_annotations")
        dataset_dir = os.path.join(here, "resources")
        OnDiskFiles().setup_dataset(dataset_dir, self._max_size)
        ManifestDataFrame().setup_dataframe(dataset_dir)
        errors = get_errors()
        self.assertEqual(4, len(errors))

        fix_errors(errors)

        remaining_errors = get_errors()

        self.assertEqual(0, len(remaining_errors))


if __name__ == "__main__":
    unittest.main()

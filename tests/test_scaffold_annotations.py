import unittest

import dulwich.porcelain
import dulwich.repo

from gitresources import dulwich_checkout, setup_resources


class ScaffoldAnnotationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._repo = setup_resources()

    def setUp(self):
        dulwich_checkout(self._repo, b"main")

    def tearDown(self):
        dulwich.porcelain.stash_push(self._repo)
        dulwich.porcelain.stash_drop(self._repo, 1)

    def test_clear_deprecated_annotations(self):
        dulwich_checkout(self._repo, b"origin/no_banner_no_scaffold_annotations")

    def test_annotate_bare_scaffold(self):
        dulwich_checkout(self._repo, b"origin/no_banner_no_scaffold_annotations")


if __name__ == "__main__":
    unittest.main()

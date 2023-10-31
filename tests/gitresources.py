import os.path
import sys

import dulwich.repo
import dulwich.porcelain
import dulwich.client
import dulwich.index

LOCAL_REMOTE_PREFIX = b"refs/remotes/"

here = os.path.abspath(os.path.dirname(__file__))


def setup_resources():
    url = "https://github.com/ABI-Software/sparc-dataset-curation-test-resources.git"
    environment_location = os.environ.get("SPARC_DATASET_CURATION_TEST_RESOURCES", "<not-set>")
    default_resources_path = os.path.join(here, "resources")
    readme_file = os.path.join(default_resources_path, "README.rst")
    if os.path.isfile(os.path.join(environment_location, "README.rst")):
        repo = dulwich.repo.Repo(environment_location, bare=False)
    elif os.path.isfile(readme_file):
        repo = dulwich.repo.Repo(default_resources_path, bare=False)
    else:
        repo = dulwich.porcelain.clone(url, os.path.join(here, "resources"))
        if not os.path.isfile(readme_file):
            sys.exit(1)

    return repo


def dulwich_checkout(repo, target):
    dulwich.porcelain.checkout_branch(repo, target, force=True)
    dulwich_clean(repo, repo.path)


def dulwich_clean(repo, target_dir):
    dulwich.porcelain.clean(repo, target_dir)


def dulwich_proper_stash_and_drop(repo):
    dulwich.porcelain.stash_push(repo)
    for e in dulwich.porcelain.stash_list(repo):
        dulwich.porcelain.reset(repo, "hard", e[1].old_sha)
    dulwich.porcelain.stash_drop(repo, 0)

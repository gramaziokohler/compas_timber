from __future__ import print_function

import os

from compas_invocations2 import build
from compas_invocations2 import docs
from compas_invocations2 import style
from compas_invocations2 import tests
from compas_invocations2 import grasshopper

from invoke.collection import Collection
from invoke.exceptions import Exit
import tomlkit


def _get_version_from_toml() -> str:
    with open("pyproject.toml", "r") as f:
        pyproject_data = tomlkit.load(f)
    if not pyproject_data:
        raise Exit("Failed to load pyproject.toml.")

    version = pyproject_data.get("tool", {}).get("bumpversion", {}).get("current_version", None)
    if not version:
        raise Exit("Failed to get version from pyproject.toml. Please provide a version number.")
    return version


def _get_package_name() -> str:
    with open("pyproject.toml", "r") as f:
        pyproject_data = tomlkit.load(f)
    if not pyproject_data:
        raise Exit("Failed to load pyproject.toml.")

    name = pyproject_data.get("project", {}).get("name", None)
    if not name:
        raise Exit("Failed to get package name from pyproject.toml.")
    return name


ns = Collection(
    docs.help,
    style.check,
    style.lint,
    style.format,
    docs.docs,
    docs.linkcheck,
    tests.test,
    tests.testdocs,
    tests.testcodeblocks,
    build.prepare_changelog,
    build.clean,
    build.release,
    build.build_cpython_ghuser_components,
    grasshopper.yakerize,
    grasshopper.publish_yak,
    grasshopper.update_gh_header,
)

ns.configure(
    {
        "base_folder": os.path.dirname(__file__),
        "ghuser_cpython": {
            "source_dir": "src/compas_timber/ghpython/components_cpython",
            "target_dir": "src/compas_timber/ghpython/components_cpython/ghuser",
            "prefix": "CT: ",
        },
    }
)

from __future__ import print_function

import os
from pathlib import Path

from compas_invocations2 import build
from compas_invocations2 import docs
from compas_invocations2 import style
from compas_invocations2 import tests
from compas_invocations2 import grasshopper

from invoke.collection import Collection
from invoke.tasks import task
from invoke.exceptions import Exit
import tomlkit


def _get_version_from_toml(toml_file: str) -> str:
    with open(toml_file, "r") as f:
        pyproject_data = tomlkit.load(f)
    if not pyproject_data:
        raise Exit("Failed to load pyproject.toml.")

    version = pyproject_data.get("tool", {}).get("bumpversion", {}).get("current_version", None)
    if not version:
        raise Exit("Failed to get version from pyproject.toml. Please provide a version number.")
    return version


@task(help={"version": "New minimum version to set in the header. If not provided, current version is used."})
def update_gh_header(ctx, version=None):
    """Update the minimum version header of all CPython Grasshopper components."""
    version = version or _get_version_from_toml("pyproject.toml")

    new_header = f"#r: compas_timber>={version}"

    for file in Path(ctx.ghuser_cpython.source_dir).glob("**/code.py"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                original_content = f.readlines()
            with open(file, "w", encoding="utf-8") as f:
                for line in original_content:
                    if line.startswith("# r: compas_timber"):
                        f.write(new_header + "\n")
                    else:
                        f.write(line)
            print(f"✅ Updated: {file}")
        except Exception as e:
            print(f"❌ Failed to update {file}: {e}")


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
    build.build_ghuser_components,
    build.build_cpython_ghuser_components,
    grasshopper.yakerize,
    grasshopper.publish_yak,
    update_gh_header,
)

ns.configure(
    {
        "base_folder": os.path.dirname(__file__),
        "ghuser": {
            "source_dir": "src/compas_timber/ghpython/components",
            "target_dir": "src/compas_timber/ghpython/components/ghuser",
            "prefix": "CT: ",
        },
        "ghuser_cpython": {
            "source_dir": "src/compas_timber/ghpython/components_cpython",
            "target_dir": "src/compas_timber/ghpython/components_cpython/ghuser",
            "prefix": "CT: ",
        },
    }
)

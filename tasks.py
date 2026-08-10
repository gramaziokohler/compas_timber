from __future__ import print_function

import os
import re

from compas_invocations2 import build
from compas_invocations2 import docs
from compas_invocations2 import mkdocs
from compas_invocations2 import style
from compas_invocations2 import tests

import invoke
from invoke.collection import Collection


@invoke.task
def sync_authors(ctx):
    """Populates the authors list in pyproject.toml and the BibTeX authors in docs/citing.md from CITATION.cff (names only)."""
    import tomlkit
    import yaml

    with open(os.path.join(ctx.base_folder, "CITATION.cff"), encoding="utf-8") as file:
        cff = yaml.safe_load(file)

    # person authors carry given-names/family-names; entity authors (e.g. a lab) carry a single "name" key.
    # names only, deliberately: PyPI renders just the first author when emails are present
    # (https://github.com/pypi/warehouse/issues/12877). From 2027 on, check whether that issue has been
    # fixed — if it has, restore the emails from CITATION.cff here
    names = [" ".join(filter(None, (author.get("given-names"), author.get("family-names")))) or author.get("name", "") for author in cff["authors"]]

    with open(os.path.join(ctx.base_folder, "pyproject.toml"), encoding="utf-8") as file:
        pyproject = tomlkit.parse(file.read())

    authors = tomlkit.array()
    authors.multiline(True)
    for name in names:
        entry = tomlkit.inline_table()
        entry["name"] = name
        authors.append(entry)
    pyproject["project"]["authors"] = authors

    with open(os.path.join(ctx.base_folder, "pyproject.toml"), "w", encoding="utf-8") as file:
        file.write(tomlkit.dumps(pyproject))

    # BibTeX wants "Family, Given"; entity authors are wrapped in braces so BibTeX takes the name literally
    bibtex_names = []
    for author in cff["authors"]:
        if author.get("family-names"):
            bibtex_names.append(", ".join(filter(None, (author["family-names"], author.get("given-names")))))
        else:
            bibtex_names.append("{{{}}}".format(author.get("name", "")))

    citing_path = os.path.join(ctx.base_folder, "docs", "citing.md")
    with open(citing_path, encoding="utf-8") as file:
        citing = file.read()

    block = "author={\n" + " and\n".join("        " + name for name in bibtex_names) + "\n    }"
    citing = re.sub(r"author={.*?\n    }", block, citing, count=1, flags=re.DOTALL)

    with open(citing_path, "w", encoding="utf-8") as file:
        file.write(citing)

    print("Synced {} authors from CITATION.cff into pyproject.toml and docs/citing.md".format(len(names)))


@invoke.task(pre=[sync_authors])
def pre_build(ctx):
    """Pre-build steps: bring the pyproject.toml authors list in sync with CITATION.cff."""


ns = Collection(
    docs.help,
    style.check,
    style.lint,
    style.format,
    mkdocs.docs,
    tests.test,
    tests.testdocs,
    tests.testcodeblocks,
    build.prepare_changelog,
    build.clean,
    build.release,
    sync_authors,
    pre_build,
)


ns.configure(
    {
        "base_folder": os.path.dirname(__file__),
    }
)

from __future__ import print_function

import os
from pathlib import Path

import compas_pb
from compas_invocations2 import build
from compas_invocations2 import docs
from compas_invocations2 import mkdocs
from compas_invocations2 import style
from compas_invocations2 import tests
from compas_pb.invocations import create_class_assets
from compas_pb.invocations import create_proto_bundle
from compas_pb.invocations import generate_proto_classes
from invoke import task
from invoke.collection import Collection


@task
def sync_authors(ctx):
    """Populates the authors list in pyproject.toml from CITATION.cff (names only).

    Runs as part of `pre-build`, so the release pipeline picks up new authors
    without anyone having to run it by hand. The docs read CITATION.cff directly
    (see scripts/mkdocs_hooks.py).
    """
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

    print("Synced {} authors from CITATION.cff into pyproject.toml".format(len(names)))


@task(pre=[sync_authors])
def pre_build(ctx):
    """Generate the Python protobuf bindings the package imports at runtime.

    Python only, and deliberately so: this runs on every lint/test/wheel job, and
    the other languages need protoc plugins (and node, for TypeScript) that those
    jobs have no other use for. The release assets are built by `create-class-assets`
    in its own job instead.

    Also syncs the pyproject.toml authors from CITATION.cff (see `sync_authors`).
    """
    generate_proto_classes(ctx)


ns = Collection(
    docs.help,
    style.check,
    style.lint,
    style.format,
    mkdocs.docs,
    tests.test,
    tests.testdocs,
    tests.testcodeblocks,
    build.clean,
    sync_authors,
    pre_build,
    generate_proto_classes,
    create_proto_bundle,
    create_class_assets,
)


ns.configure(
    {
        "base_folder": os.path.dirname(__file__),
        "proto_folder": Path("./src") / "compas_timber" / "proto",
        # include/out paths are rooted at ./src so that protoc derives the python
        # import of a cross-file proto import from its full package path, i.e.
        # `from compas_timber.proto import elements_pb2` rather than a bare
        # `import elements_pb2` which would only resolve via sys.path hacking.
        "proto_include_paths": [Path("./src"), compas_pb.PROTOBUF_DEFS],
        "proto_out_folder": Path("./src"),
        # compas_timber owns these .proto files, so it publishes the schema bundle
        # and the per-language bindings itself. `package_name` labels those release
        # assets; without it compas_pb's tasks would name them after compas_pb.
        "package_name": "compas_timber",
        # Non-Python bindings are generated only to be zipped, so keep them out of
        # src/ (the default) and in the build directory that `invoke clean` owns.
        "generated_folder": Path("./dist") / "generated",
    }
)

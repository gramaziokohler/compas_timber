from __future__ import print_function

import os
from pathlib import Path

import compas_pb
from compas_invocations2 import build
from compas_invocations2 import docs
from compas_invocations2 import mkdocs
from compas_invocations2 import style
from compas_invocations2 import tests
from compas_pb.invocations import generate_proto_classes
from invoke import task
from invoke.collection import Collection


@task
def pre_build(ctx):
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
    build.prepare_changelog,
    build.clean,
    build.release,
    pre_build,
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
    }
)

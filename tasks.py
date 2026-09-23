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
def pre_build(ctx):
    """Generate the Python protobuf bindings the package imports at runtime.

    Python only, and deliberately so: this runs on every lint/test/wheel job, and
    the other languages need protoc plugins (and node, for TypeScript) that those
    jobs have no other use for. The release assets are built by `create-class-assets`
    in its own job instead.
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

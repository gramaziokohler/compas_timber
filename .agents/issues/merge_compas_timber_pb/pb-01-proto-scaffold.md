# PB-01: Proto scaffold

## Parent

[merge_compas_timber_pb.md](merge_compas_timber_pb.md)

## What to build

Set up the `compas_timber.proto` subpackage so the build toolchain can generate protobuf Python bindings from the existing IDL files.

- Copy the three `.proto` files from `compas_timber_pb/IDL/compas_timber_pb/generated/` (`elements.proto`, `processing.proto`, `building_plan.proto`) into `src/compas_timber/proto/`. Inside each file, replace the package/import namespace prefix `compas_timber_pb` with `compas_timber.proto`.
- Create `src/compas_timber/proto/__init__.py` (empty / minimal — serializers register themselves via the entry point, no explicit exports needed).
- Add `src/compas_timber/proto/*_pb2.py` (and `*_pb2_grpc.py` if emitted) to `.gitignore` so generated files are never committed.
- Add a `pre_build` task to `tasks.py`, following the pattern in `antikythera-backend/tasks.py`: import `generate_proto_classes` from `compas_pb.invocations`, define `@task def pre_build(ctx)`, add it to `ns`, and configure `ns` with `proto_folder`, `proto_include_paths`, and `proto_out_folder` pointing into `src/compas_timber/proto/`. Also import `compas_pb` and add `compas_pb.PROTOBUF_DEFS` to `proto_include_paths`.
- Add `compas_pb >= 0.4.0` to the `dependencies` list in `pyproject.toml` under `[project]`.
- Update the `[build-system]` `requires` list in `pyproject.toml` to include `compas_pb` and `grpcio-tools` (needed at build time to run `pre_build`).

## Acceptance criteria

- [x] `src/compas_timber/proto/` contains `elements.proto`, `processing.proto`, `building_plan.proto` with namespaces updated to `compas_timber.proto`
- [x] `src/compas_timber/proto/__init__.py` exists
- [x] `.gitignore` excludes `*_pb2.py` (and `*_pb2_grpc.py`) under `src/compas_timber/proto/`
- [x] `invoke pre_build` runs without error and generates `*_pb2.py` files under `src/compas_timber/proto/`
- [x] `compas_pb >= 0.4.0` is listed in `[project] dependencies` in `pyproject.toml`
- [x] The generated `*_pb2.py` files are not tracked by git (gitignore patterns added; verified once files exist)

## Blocked by

None — can start immediately.

# PB-06: Round-trip verification and bug fixing

## Parent

[merge_compas_timber_pb.md](merge_compas_timber_pb.md)

## What to build

Run the full test suite against the merged implementation, diagnose any failures, and iterate until all proto-related tests pass end-to-end.

This is an investigative + fixing slice. The expected failure modes include:

- Proto namespace mismatches (e.g. a `.proto` import path still referencing `compas_timber_pb`)
- Missing `invoke pre_build` before the test run causing `ModuleNotFoundError` on `*_pb2` imports
- Entry point not discovered because the package was not re-installed after adding it (`pip install -e .`)
- Serializer/deserializer not registered at import time (entry point target module raises on import)
- Field name or type mismatches between the ported serializers and the updated proto messages

Work to do:

1. Run `invoke pre_build` to generate `*_pb2.py` files.
2. Re-install the package (`uv pip install -e ".[dev]"`) so the new entry point is registered.
3. Run `invoke test` (or `pytest tests/test_proto_beam.py tests/test_proto_building_plan.py -v`) and record all failures.
4. Fix each failure at its root cause. Do not skip or xfail tests that should pass — fix them.
5. Repeat until `invoke test` passes with no errors or unexpected failures.

## Acceptance criteria

- [x] `invoke pre_build` completes without error
- [x] `tests/test_proto_beam.py` — all tests pass
- [x] `tests/test_proto_building_plan.py` — all tests pass
- [x] `invoke test` (full suite) passes with no regressions in existing non-proto tests
- [x] No `compas_timber_pb` imports remain anywhere under `src/compas_timber/` or `tests/`

## Blocked by

- [pb-03-beam-processing-serializers.md](pb-03-beam-processing-serializers.md)
- [pb-04-building-plan-serializers.md](pb-04-building-plan-serializers.md)
- [pb-05-ci-workflow-upgrade.md](pb-05-ci-workflow-upgrade.md)

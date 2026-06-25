# PB-04: BuildingPlan + BuildingPlanModelContainer serializers

## Parent

[merge_compas_timber_pb.md](merge_compas_timber_pb.md)

## What to build

Extend `proto/data.py` with the remaining serializers (`BuildingPlan`, `Step`, `BuildingPlanModelContainer`) and verify them with a ported test suite.

- Add the `BuildingPlan`, `Step`, and `BuildingPlanModelContainer` serializer/deserializer pairs to `src/compas_timber/proto/data.py`, ported from `compas_timber_pb/src/compas_timber_pb/data.py`. Update imports:
  - `compas_timber_pb.generated` → `compas_timber.proto`
  - `compas_timber_pb.planning import BuildingPlanModelContainer` → `compas_timber.planning import BuildingPlanModelContainer`
- Add `tests/test_proto_building_plan.py`, ported from `compas_timber_pb/tests/test_building_plan.py`. Update the `BuildingPlanModelContainer` import to come from `compas_timber.planning`.

## Acceptance criteria

- [x] `proto/data.py` contains serializers for `BuildingPlan`, `Step`, and `BuildingPlanModelContainer`
- [x] No imports from `compas_timber_pb` remain anywhere in `proto/data.py`
- [x] `tests/test_proto_building_plan.py` passes: all four test cases (timber model, just model, container serialization, container shapes)
- [x] `invoke test` passes

## Blocked by

- [pb-01-proto-scaffold.md](pb-01-proto-scaffold.md)
- [pb-02-building-plan-container.md](pb-02-building-plan-container.md)
- [pb-03-beam-processing-serializers.md](pb-03-beam-processing-serializers.md)

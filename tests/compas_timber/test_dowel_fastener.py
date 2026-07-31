import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import Dowel
from compas_timber.fasteners import DowelFastener
from compas_timber.fasteners import FastenerAnchor
from compas_timber.model import TimberModel


def test_dowel():
    dowel = Dowel(diameter=10, length=100)
    assert dowel.diameter == 10
    assert dowel.length == 100


def test_dowel_centerline():
    dowel = Dowel(diameter=10, length=100)
    assert dowel.centerline.start == Point(0, 0, 0)
    assert dowel.centerline.end == Point(0, 0, -100)


@pytest.mark.requires_occ
def test_dowel_geometry():
    dowel = Dowel(diameter=10, length=100)
    geo = dowel.compute_elementgeometry()
    assert geo.is_valid
    assert geo.is_manifold


def test_dowel_deserialization():
    dowel = Dowel(diameter=10, length=100, placement_frame=Frame(Point(1, 2, 3), [1, 0, 0], [0, 1, 0]))
    rec_dowel = json_loads(json_dumps(dowel))

    assert rec_dowel.diameter == dowel.diameter
    assert rec_dowel.length == dowel.length


def test_dowel_fastener_accepts_axis_only():
    assert DowelFastener.ACCEPTS is AnchorKind.AXIS


def test_dowel_fastener_rejects_wrong_anchor_kind():
    fastener = DowelFastener(diameter=8, length=50)
    anchor = FastenerAnchor(frame=Frame.worldXY(), kind=AnchorKind.FACE, elements=[])

    with pytest.raises(ValueError):
        fastener.bind([anchor])


def test_dowel_fastener_bind_places_one_dowel_per_anchor():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=3)

    fastener = DowelFastener(diameter=8, length=50)
    anchors = joint.fastener_anchors.of_kind(AnchorKind.AXIS)
    fastener.bind(anchors)

    assert len(fastener.parts) == len(anchors)
    assert all(isinstance(part, Dowel) for part in fastener.parts)
    assert all(part.diameter == 8 and part.length == 50 for part in fastener.parts)


def test_dowel_fastener_applies_drilling_features():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=3)

    fastener = DowelFastener(diameter=8, length=50)
    fastener.bind(joint.fastener_anchors.of_kind(AnchorKind.AXIS))
    model.add_fastener(fastener, joint.beams)

    model.process_fasteners()

    feature_names = [type(feature).__name__ for feature in cross_beam.features]
    assert feature_names.count("Drilling") == 1


def test_dowel_fastener_scopes_features_to_each_anchors_elements():
    """A single fastener bound to anchors from unrelated beam pairs must only drill each anchor's own elements.

    Regression test: previously `apply_fastening_features` was handed every element the fastener connects to
    anywhere in the model (the union across all its anchors), so every dowel drilled every beam instead of just
    the pair its own anchor referenced.
    """
    model = TimberModel()
    cross_beam_1 = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam_1 = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    cross_beam_2 = Beam.from_centerline(Line(Point(-100, 500, 20), Point(100, 500, 20)), width=10, height=20)
    main_beam_2 = Beam.from_centerline(Line(Point(0, 500, 20), Point(0, 500, 200)), width=10, height=20)
    model.add_elements([cross_beam_1, main_beam_1, cross_beam_2, main_beam_2])

    joint_1 = TButtJoint.create(model, main_beam_1, cross_beam_1, mill_depth=3)
    joint_2 = TButtJoint.create(model, main_beam_2, cross_beam_2, mill_depth=3)

    anchors = joint_1.fastener_anchors.of_kind(AnchorKind.AXIS) + joint_2.fastener_anchors.of_kind(AnchorKind.AXIS)

    # one fastener, bound across anchors from two unrelated joints (a batch/pattern use case `bind()` supports)
    fastener = DowelFastener(diameter=8, length=50)
    fastener.bind(anchors)
    model.add_fastener(fastener, [cross_beam_1, main_beam_1, cross_beam_2, main_beam_2])

    model.process_fasteners()

    for beam in (cross_beam_1, main_beam_1, cross_beam_2, main_beam_2):
        drillings = [f for f in beam.features if type(f).__name__ == "Drilling"]
        assert len(drillings) == 1


def test_dowel_fastener_model_deserialization():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=50, height=50)
    main_beam = Beam.from_centerline(Line(Point(1000, 0, 0), Point(1000, 1000, 0)), width=50, height=50)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=10)

    fastener = DowelFastener(diameter=8, length=100)
    fastener.bind(joint.fastener_anchors.of_kind(AnchorKind.AXIS))
    model.add_fastener(fastener, joint.beams)

    reconstructed_model = json_loads(json_dumps(model))

    rec_fasteners = list(reconstructed_model.fasteners)
    assert len(rec_fasteners) == 1
    assert isinstance(rec_fasteners[0], DowelFastener)
    assert len(rec_fasteners[0].parts) == len(fastener.parts)
    assert all(isinstance(part, Dowel) for part in rec_fasteners[0].parts)

    # the part's `elements` (restored from `element_guids` by TimberModel.__from_data__) must reference the
    # *reconstructed* model's own beam instances, not the original (pre-serialization) ones
    rec_beams = list(reconstructed_model.beams)
    for part in rec_fasteners[0].parts:
        assert part.elements
        assert all(element in rec_beams for element in part.elements)

    # and the restored elements must be usable, i.e. `process_fasteners()` works on the reconstructed model too
    reconstructed_model.process_fasteners()
    rec_cross_beam = next(b for b in rec_beams if b.width == 50 and b.height == 50 and b.length == 2000)
    drillings = [f for f in rec_cross_beam.features if type(f).__name__ == "Drilling"]
    assert len(drillings) == 1

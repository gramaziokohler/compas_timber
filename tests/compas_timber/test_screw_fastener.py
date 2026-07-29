import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import FastenerAnchor
from compas_timber.fasteners import Screw
from compas_timber.fasteners import ScrewFastener
from compas_timber.model import TimberModel


def test_screw():
    screw = Screw(diameter=8, length=120)
    assert screw.diameter == 8
    assert screw.length == 120
    assert screw.precise is False


def test_screw_head_defaults_from_diameter():
    screw = Screw(diameter=8, length=120)
    assert screw.head_diameter == 16
    assert screw.head_length == 8


def test_screw_head_explicit_overrides():
    screw = Screw(diameter=8, length=120, head_diameter=20, head_length=10)
    assert screw.head_diameter == 20
    assert screw.head_length == 10


def test_screw_designation():
    assert Screw(diameter=8, length=120).designation == "Ø8x120"
    assert Screw(diameter=5.5, length=80).designation == "Ø5.5x80"


@pytest.mark.parametrize("name", ["8x120", "Ø8x120", "8.0x120", "D8 x 120", "8*120"])
def test_screw_from_name(name):
    screw = Screw.from_name(name)
    assert screw.diameter == 8
    assert screw.length == 120


def test_screw_from_name_invalid():
    with pytest.raises(ValueError):
        Screw.from_name("not-a-screw")


def test_screw_centerline():
    screw = Screw(diameter=8, length=120)
    assert screw.centerline.start == Point(0, 0, 0)
    assert screw.centerline.end == Point(0, 0, -120)


def test_screw_simplified_geometry_is_just_the_shank():
    screw = Screw(diameter=8, length=120)
    geo = screw.compute_elementgeometry()

    assert geo.is_valid
    assert geo.is_manifold
    assert len(geo.faces) == 3  # plain cylinder: two caps + the lateral face


def test_screw_precise_geometry_unions_head_onto_shank():
    simple = Screw(diameter=8, length=120)
    precise = Screw(diameter=8, length=120, precise=True)

    simple_geo = simple.compute_elementgeometry()
    precise_geo = precise.compute_elementgeometry()

    assert precise_geo.is_valid
    assert precise_geo.is_manifold
    # the head adds material on top of the plain shank, as a single unioned solid
    assert precise_geo.volume > simple_geo.volume
    assert precise_geo.area > simple_geo.area


def test_screw_deserialization():
    screw = Screw(diameter=8, length=120, precise=True, head_diameter=20, head_length=10)
    rec_screw = json_loads(json_dumps(screw))

    assert rec_screw.diameter == screw.diameter
    assert rec_screw.length == screw.length
    assert rec_screw.precise == screw.precise
    assert rec_screw.head_diameter == screw.head_diameter
    assert rec_screw.head_length == screw.head_length


def test_screw_fastener_accepts_axis_and_point():
    assert AnchorKind.AXIS in ScrewFastener.ACCEPTS
    assert AnchorKind.POINT in ScrewFastener.ACCEPTS


def test_screw_fastener_rejects_wrong_anchor_kind():
    fastener = ScrewFastener([Screw(diameter=6, length=50)])
    anchor = FastenerAnchor(frame=Frame.worldXY(), kind=AnchorKind.FACE, elements=[])

    with pytest.raises(ValueError):
        fastener.bind([anchor])


def test_screw_fastener_bind_places_the_whole_pattern_at_each_anchor():
    screws = [Screw(diameter=6, length=50), Screw(diameter=6, length=50, placement_frame=Frame(Point(5, 0, 0), [1, 0, 0], [0, 1, 0]))]
    fastener = ScrewFastener(screws)

    anchor_a = FastenerAnchor(frame=Frame.worldXY(), kind=AnchorKind.AXIS, elements=[])
    anchor_b = FastenerAnchor(frame=Frame(Point(0, 0, 100), [1, 0, 0], [0, 1, 0]), kind=AnchorKind.AXIS, elements=[])
    fastener.bind([anchor_a, anchor_b])

    assert len(fastener.parts) == len(screws) * 2
    assert all(isinstance(part, Screw) for part in fastener.parts)


def test_screw_fastener_bind_offsets_pattern_by_screw_placement_frame():
    offset_frame = Frame(Point(5, 0, 0), [1, 0, 0], [0, 1, 0])
    fastener = ScrewFastener([Screw(diameter=6, length=50, placement_frame=offset_frame)])
    anchor = FastenerAnchor(frame=Frame.worldXY(), kind=AnchorKind.AXIS, elements=[])

    fastener.bind([anchor])

    assert fastener.parts[0].frame.point == offset_frame.point


def test_screw_fastener_bind_accepts_point_anchor():
    fastener = ScrewFastener([Screw(diameter=6, length=50)])
    anchor = FastenerAnchor(frame=Frame.worldXY(), kind=AnchorKind.POINT, elements=[])

    fastener.bind([anchor])

    assert len(fastener.parts) == 1


def test_screw_fastener_applies_drilling_features():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=3)

    fastener = ScrewFastener([Screw(diameter=6, length=50)])
    fastener.bind(joint.fastener_anchors.of_kind(AnchorKind.AXIS))
    model.add_fastener(fastener, joint.beams)

    model.process_fasteners()

    feature_names = [type(feature).__name__ for feature in cross_beam.features]
    assert feature_names.count("Drilling") == 1


def test_screw_fastener_model_deserialization():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=50, height=50)
    main_beam = Beam.from_centerline(Line(Point(1000, 0, 0), Point(1000, 1000, 0)), width=50, height=50)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=10)

    fastener = ScrewFastener([Screw(diameter=8, length=100, precise=True)])
    fastener.bind(joint.fastener_anchors.of_kind(AnchorKind.AXIS))
    model.add_fastener(fastener, joint.beams)

    reconstructed_model = json_loads(json_dumps(model))

    rec_fasteners = list(reconstructed_model.fasteners)
    assert len(rec_fasteners) == 1
    assert isinstance(rec_fasteners[0], ScrewFastener)
    assert len(rec_fasteners[0].parts) == len(fastener.parts)
    assert all(isinstance(part, Screw) for part in rec_fasteners[0].parts)
    assert rec_fasteners[0].parts[0].precise is True

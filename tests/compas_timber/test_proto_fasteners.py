"""Protobuf round-trip tests for the anchor-based fastener system.

Covers the parts of the schema fastener.py introduces: the resolved
`Fastener` container, each concrete `FastenerPart` (`Screw`, `Dowel`,
`RectangularPlate` with its `PlateHole` entries, `GeometryPart` with its
arbitrary AnyData geometry, and the ball-node `BallNodeCore` / `BallNodeRod`
/ `BallNodePlate` trio), `BallNodeFastenerParameters`, and the two ways a
fastener actually ends up in a model: bound from a `FastenerSystem` at a
joint's anchors, or staged directly with `Fastener.add_part`.
"""

import json

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line

from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber.connections import BallNodeJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import BallNodeCore
from compas_timber.fasteners import BallNodeFastenerParameters
from compas_timber.fasteners import BallNodePlate
from compas_timber.fasteners import BallNodeRod
from compas_timber.fasteners import Dowel
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import GeometryPart
from compas_timber.fasteners import PlateHole
from compas_timber.fasteners import RectangularPlate
from compas_timber.fasteners import Screw
from compas_timber.fasteners import ScrewFastenerSystem
from compas_timber.model import TimberModel


@pytest.fixture(autouse=True)
def load_serializers():
    import compas_timber.proto.conversions  # noqa: F401


def roundtrip(obj):
    return pb_load_bts(pb_dump_bts(obj))


def assert_lossless(obj):
    other = roundtrip(obj)
    assert type(other) is type(obj)
    assert json.loads(json_dumps(other, minimal=True)) == json.loads(json_dumps(obj, minimal=True))
    assert str(other.guid) == str(obj.guid)
    return other


def test_fastener_roundtrip():
    fastener = Fastener(frame=Frame([1, 2, 3], [1, 0, 0], [0, 1, 0]), name="my-fastener")
    assert_lossless(fastener)


def test_screw_roundtrip():
    screw = Screw(
        diameter=8,
        length=120,
        precise=True,
        head_diameter=20,
        head_length=10,
        placement_frame=Frame([1, 0, 0], [1, 0, 0], [0, 1, 0]),
        element_guids=["11111111-1111-1111-1111-111111111111"],
    )
    other = assert_lossless(screw)
    assert other.diameter == screw.diameter
    assert other.precise is True
    assert other.element_guids == list(screw.element_guids)


def test_dowel_roundtrip():
    dowel = Dowel(diameter=10, length=100, placement_frame=Frame([2, 0, 0], [1, 0, 0], [0, 1, 0]))
    assert_lossless(dowel)


def test_plate_hole_roundtrip():
    hole = PlateHole(Frame([1, 1, 0], [1, 0, 0], [0, 1, 0]), diameter=6, height=8, apply_drilling=True, drilling_depth=5, drilling_diameter=3)
    other = assert_lossless(hole)
    assert other.diameter == hole.diameter
    assert other.drilling_depth == hole.drilling_depth


def test_rectangular_plate_with_holes_roundtrip():
    hole = PlateHole(Frame([1, 1, 0], [1, 0, 0], [0, 1, 0]), diameter=6, height=8)
    plate = RectangularPlate(width=40, height=50, thickness=5, recess=5, recess_offset=1, holes=[hole])

    other = roundtrip(plate)

    assert other.width == plate.width
    assert other.height == plate.height
    assert other.thickness == plate.thickness
    assert other.recess == plate.recess
    assert other.recess_offset == plate.recess_offset
    assert len(other.holes) == 1
    assert isinstance(other.holes[0], PlateHole)
    assert other.holes[0].diameter == hole.diameter


def test_geometry_part_roundtrip():
    mesh = Box(1, 1, 1).to_mesh()
    part = GeometryPart(mesh, frame=Frame([5, 5, 5], [1, 0, 0], [0, 1, 0]))

    other = roundtrip(part)

    assert isinstance(other._raw_geometry, Mesh)
    assert other.frame.point == part.frame.point


def test_ball_node_core_roundtrip():
    core = BallNodeCore(diameter=8, frame=Frame([0, 0, 0], [1, 0, 0], [0, 1, 0]))
    other = assert_lossless(core)
    assert other.diameter == core.diameter


def test_ball_node_rod_roundtrip():
    rod = BallNodeRod(length=10, diameter=2.5, frame=Frame([0, 0, 1], [1, 0, 0], [0, 1, 0]))
    other = assert_lossless(rod)
    assert other.length == rod.length
    assert other.diameter == rod.diameter


def test_ball_node_plate_roundtrip():
    plate = BallNodePlate(x_size=10, y_size=30, thickness=2, frame=Frame([0, 0, 2], [1, 0, 0], [0, 1, 0]), plate_depth=10)
    other = assert_lossless(plate)
    assert other.x_size == plate.x_size
    assert other.plate_depth == plate.plate_depth


def test_ball_node_fastener_parameters_roundtrip():
    params = BallNodeFastenerParameters(ball_diameter=8, rods_length=10, plate_thickness=2, plate_depth=10)
    assert_lossless(params)


def test_screw_fastener_model_roundtrip():
    """A ScrewFastenerSystem bound at a TButtJoint's anchors, round-tripped as part of a whole model."""
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line([0, 0, 0], [2000, 0, 0]), width=50, height=50)
    main_beam = Beam.from_centerline(Line([1000, 0, 0], [1000, 1000, 0]), width=50, height=50)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=10)
    system = ScrewFastenerSystem([Screw(diameter=8, length=100, precise=True)])
    fastener = system.bind(joint.fastener_anchors.of_kind(AnchorKind.AXIS))
    model.add_fastener(fastener, joint.beams)

    rec_model = pb_load_bts(pb_dump_bts(model))

    rec_fasteners = list(rec_model.fasteners)
    assert len(rec_fasteners) == 1
    assert isinstance(rec_fasteners[0], Fastener)
    assert len(rec_fasteners[0].parts) == len(fastener.parts)
    assert all(isinstance(part, Screw) for part in rec_fasteners[0].parts)
    assert rec_fasteners[0].parts[0].precise is True

    rec_beams = list(rec_model.beams)
    for part in rec_fasteners[0].parts:
        assert part.elements
        assert all(element in rec_beams for element in part.elements)

    rec_model.process_fasteners()
    rec_cross_beam = next(b for b in rec_beams if b.length == 2000)
    drillings = [f for f in rec_cross_beam.features if type(f).__name__ == "Drilling"]
    assert len(drillings) == 1


def test_ball_node_fastener_model_roundtrip():
    """A BallNodeJoint's fastener (core/rods/plates hierarchy) and its shaping parameters both survive."""
    model = TimberModel()
    centerlines = [Line([1, 1, 1], [100, 100, 100]), Line([1, 1, 1], [100, -50, 30]), Line([1, 1, 1], [-100, -20, -60]), Line([1, 1, 1], [-100, 100, 80])]
    beams = [Beam.from_centerline(centerline, 10, 30) for centerline in centerlines]
    for beam in beams:
        model.add_element(beam)

    parameters = BallNodeFastenerParameters(ball_diameter=8, rods_length=10, plate_thickness=2, plate_depth=10)
    BallNodeJoint.create(model, *beams, parameters=parameters)

    rec_model = pb_load_bts(pb_dump_bts(model))

    rec_joints = list(rec_model.joints)
    assert len(rec_joints) == 1
    assert isinstance(rec_joints[0], BallNodeJoint)
    assert rec_joints[0].parameters.__data__ == parameters.__data__

    rec_fasteners = list(rec_model.fasteners)
    assert len(rec_fasteners) == 1
    fastener = rec_fasteners[0]
    assert isinstance(fastener, Fastener)
    assert len(fastener.parts) == 1
    core = fastener.parts[0]
    assert isinstance(core, BallNodeCore)
    assert len(core.parts) == 4
    assert all(isinstance(rod, BallNodeRod) for rod in core.parts)
    for rod in core.parts:
        assert len(rod.parts) == 1
        assert isinstance(rod.parts[0], BallNodePlate)
    assert len(fastener.all_parts) == 9


def test_fastener_with_geometry_part_model_roundtrip():
    """A Fastener built directly (no system), staging a GeometryPart, as used for custom/library fasteners."""
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line([-100, 0, 20], [100, 0, 20]), width=10, height=20)
    main_beam = Beam.from_centerline(Line([0, 0, 20], [0, 0, 200]), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    mesh = Box(1, 1, 1).to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(mesh, frame=Frame([1, 0, 0], [0, 1, 0], [0, 0, 1])))
    fastener.add_part(GeometryPart(mesh, frame=Frame([0, 1, 0], [1, 0, 0], [0, 0, 1])))
    model.add_fastener(fastener, [main_beam, cross_beam])

    rec_model = pb_load_bts(pb_dump_bts(model))

    rec_fasteners = list(rec_model.fasteners)
    assert len(rec_fasteners) == 1
    assert len(rec_fasteners[0].parts) == 2
    assert all(isinstance(part, GeometryPart) for part in rec_fasteners[0].parts)

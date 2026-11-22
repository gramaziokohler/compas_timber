import math

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere as SphereGeometry
from compas.geometry import Vector
from compas.tolerance import Tolerance

from compas_timber.btlx import BTLxReader
from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication.chamfer import Chamfer
from compas_timber.fabrication.chamfer import ChamferExitType
from compas_timber.fabrication.marking import Marking
from compas_timber.fabrication.marking import MarkingStyleType
from compas_timber.fabrication.planing import Planing
from compas_timber.fabrication.ridge_valley_cut import RidgeValleyCut
from compas_timber.fabrication.saw_cut import SawCut
from compas_timber.fabrication.saw_cut import SawCutMachiningLimits
from compas_timber.fabrication.sphere import Sphere
from compas_timber.fabrication.triangle_cut import TriangleCut
from compas_timber.model import TimberModel

LENGTH, WIDTH, HEIGHT = 1000.0, 100.0, 200.0
BEAM_VOLUME = LENGTH * WIDTH * HEIGHT
ROTATED_FRAME = Frame([100.0, -200.0, 300.0], [0.0, 1.0, 0.0], [1.0, 0.0, 1.0])


def make_beam(frame=None):
    return Beam(frame or Frame.worldXY(), LENGTH, WIDTH, HEIGHT)


def cut(processing, frame=None):
    """Apply the processing to a new beam, returning the beam and the resulting element geometry."""
    beam = make_beam(frame)
    beam.add_features([processing])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    return beam, geometry


def removed(processing, frame=None):
    return BEAM_VOLUME - cut(processing, frame)[1].volume


def is_solid(beam, geometry, ref_side_index, x, y, z):
    """Whether there is material at a point given in the coordinates of a reference side."""
    point = beam.ref_sides[ref_side_index].to_world_coordinates(Point(x, y, z))
    return geometry.contains(point.transformed(beam.transformation_to_local()))


def assert_serializes(processing, expected_data):
    assert processing.__data__ == expected_data
    restored = json_loads(json_dumps(processing))
    assert type(restored) is type(processing)
    assert restored.__data__ == processing.__data__


@pytest.mark.parametrize(
    "cls, kwargs",
    [
        (RidgeValleyCut, {"start_x": 100000.1}),
        (RidgeValleyCut, {"start_y": -0.1}),
        (RidgeValleyCut, {"start_depth": 50000.1}),
        (RidgeValleyCut, {"inclination_ref_side": 90.0}),
        (RidgeValleyCut, {"inclination_opp_side": -90.0}),
        (RidgeValleyCut, {"start_limited": "yes"}),
        (RidgeValleyCut, {"end_limited": 1}),
        (RidgeValleyCut, {"length": -0.1}),
        (RidgeValleyCut, {"angle_ref_edge_start": 0.0}),
        (RidgeValleyCut, {"angle_ref_edge_end": 180.0}),
        (RidgeValleyCut, {"angle_opp_edge_start": 0.0}),
        (RidgeValleyCut, {"angle_opp_edge_end": 180.0}),
        (SawCut, {"start_x": -100000.1}),
        (SawCut, {"start_y": 50000.1}),
        (SawCut, {"start_depth": -50000.1}),
        (SawCut, {"angle": 180.1}),
        (SawCut, {"inclination": 0.0}),
        (SawCut, {"bevel": 90.0}),
        (SawCut, {"length": 100000.1}),
        (SawCut, {"depth": -1.0}),
        (SawCut, {"machining_limits": "yes"}),
        (SawCut, {"machining_limits": {"FaceLimitedTop": True}}),
        (SawCut, {"tool_position": "top"}),
        (TriangleCut, {"start_x": 100000.1}),
        (TriangleCut, {"start_y": 50000.1}),
        (TriangleCut, {"start_depth": 50000.1}),
        (TriangleCut, {"normal_1_x": 50000.1}),
        (TriangleCut, {"normal_1_y": 50000.1}),
        (TriangleCut, {"normal_1_z": 50000.1}),
        (TriangleCut, {"normal_2_x": -50000.1}),
        (TriangleCut, {"normal_2_y": -50000.1}),
        (TriangleCut, {"normal_2_z": -50000.1}),
        (Chamfer, {"start_x": 100000.1}),
        (Chamfer, {"start_limited": "no"}),
        (Chamfer, {"end_limited": "no"}),
        (Chamfer, {"length": -0.1}),
        (Chamfer, {"depth": 100.1}),
        (Chamfer, {"chamfer_edge_12": 1}),
        (Chamfer, {"chamfer_edge_23": 1}),
        (Chamfer, {"chamfer_edge_34": 1}),
        (Chamfer, {"chamfer_edge_41": 1}),
        (Chamfer, {"chamfer_exit": "bevel"}),
        (Planing, {"start_x": 100000.1}),
        (Planing, {"length": 100000.1}),
        (Planing, {"depth": 50.1}),
        (Planing, {"start_limited": "no"}),
        (Planing, {"end_limited": "no"}),
        (Planing, {"plane_side_1": 1}),
        (Planing, {"plane_side_2": 1}),
        (Planing, {"plane_side_3": 1}),
        (Planing, {"plane_side_4": 1}),
        (Sphere, {"orientation": "middle"}),
        (Sphere, {"start_x": 100000.1}),
        (Sphere, {"start_y": 50000.1}),
        (Sphere, {"start_depth": 50000.1}),
        (Sphere, {"length": -0.1}),
        (Sphere, {"radius": -0.1}),
        (Sphere, {"start_offset": 50000.1}),
        (Marking, {"start_x": 100000.1}),
        (Marking, {"start_y": 50000.1}),
        (Marking, {"angle": 180.1}),
        (Marking, {"length_limited": "no"}),
        (Marking, {"length": -0.1}),
        (Marking, {"width": 50000.1}),
        (Marking, {"interior_angle": 180.0}),
        (Marking, {"style": "triple"}),
    ],
)
def test_limits_are_rejected(cls, kwargs):
    with pytest.raises(ValueError):
        cls(**kwargs)


def test_params_ridge_valley_cut():
    params = RidgeValleyCut(start_x=10.0, inclination_opp_side=-30.0, end_limited=True, length=200.0, angle_opp_edge_end=60.0, ref_side_index=1).params
    assert params.header_attributes["ReferencePlaneID"] == "2"
    assert list(params.as_dict().items()) == [
        ("StartX", "10.000"),
        ("StartY", "50.000"),
        ("StartDepth", "0.000"),
        ("InclinationRefSide", "45.000"),
        ("InclinationOppSide", "-30.000"),
        ("StartLimited", "no"),
        ("EndLimited", "yes"),
        ("Length", "200.000"),
        ("AngleRefEdgeStart", "90.000"),
        ("AngleRefEdgeEnd", "90.000"),
        ("AngleOppEdgeStart", "90.000"),
        ("AngleOppEdgeEnd", "60.000"),
    ]


def test_params_saw_cut():
    params = SawCut(start_x=10.0, bevel=5.0, machining_limits=SawCutMachiningLimits(face_limited_end=False)).params
    assert params.header_attributes["ToolPosition"] == "left"
    assert list(params.as_dict().items()) == [
        ("StartX", "10.000"),
        ("StartY", "0.000"),
        ("StartDepth", "0.000"),
        ("Angle", "90.000"),
        ("Inclination", "90.000"),
        ("Bevel", "5.000"),
        ("Length", "100.000"),
        ("Depth", "50.000"),
        ("MachiningLimits", {"FaceLimitedStart": "yes", "FaceLimitedEnd": "no", "FaceLimitedBottom": "yes"}),
    ]


def test_saw_cut_machining_limits_are_optional():
    assert "MachiningLimits" not in SawCut().params.as_dict()


def test_params_triangle_cut():
    assert list(TriangleCut(normal_1_y=0.5, normal_2_z=-0.5).params.as_dict().items()) == [
        ("StartX", "0.000"),
        ("StartY", "60.000"),
        ("StartDepth", "60.000"),
        ("Normal1X", "1.000"),
        ("Normal1Y", "0.500"),
        ("Normal1Z", "0.000"),
        ("Normal2X", "1.000"),
        ("Normal2Y", "0.000"),
        ("Normal2Z", "-0.500"),
    ]


def test_params_chamfer():
    params = Chamfer(depth=5.0, chamfer_edge_23=False, chamfer_exit=ChamferExitType.ROUND).params
    assert "ReferencePlaneID" not in params.header_attributes
    assert list(params.as_dict().items()) == [
        ("StartX", "0.000"),
        ("StartLimited", "no"),
        ("EndLimited", "no"),
        ("Length", "0.000"),
        ("Depth", "5.000"),
        ("ChamferEdge12", "yes"),
        ("ChamferEdge23", "no"),
        ("ChamferEdge34", "yes"),
        ("ChamferEdge41", "yes"),
        ("ChamferExit", "round"),
    ]


def test_params_planing():
    params = Planing(start_limited=True, plane_side_4=False).params
    assert "ReferencePlaneID" not in params.header_attributes
    assert list(params.as_dict().items()) == [
        ("StartX", "0.000"),
        ("Length", "0.000"),
        ("Depth", "1.000"),
        ("StartLimited", "yes"),
        ("EndLimited", "no"),
        ("PlaneSide1", "yes"),
        ("PlaneSide2", "yes"),
        ("PlaneSide3", "yes"),
        ("PlaneSide4", "no"),
    ]


def test_params_sphere():
    assert list(Sphere(orientation="end", start_offset=5.0).params.as_dict().items()) == [
        ("Orientation", "end"),
        ("StartX", "0.000"),
        ("StartY", "60.000"),
        ("StartDepth", "60.000"),
        ("Length", "50.000"),
        ("Radius", "50.000"),
        ("StartOffset", "5.000"),
    ]


def test_params_marking():
    assert list(Marking(style=MarkingStyleType.SQUARE, length_limited=True).params.as_dict().items()) == [
        ("StartX", "0.000"),
        ("StartY", "0.000"),
        ("Angle", "0.000"),
        ("LengthLimited", "yes"),
        ("Length", "20.000"),
        ("Width", "100.000"),
        ("InteriorAngle", "90.000"),
        ("Style", "square"),
    ]


def test_scale_only_changes_lengths():
    ridge = RidgeValleyCut(start_x=1.0, start_y=2.0, start_depth=3.0, length=4.0).scaled(10.0)
    assert (ridge.start_x, ridge.start_y, ridge.start_depth, ridge.length) == (10.0, 20.0, 30.0, 40.0)
    assert (ridge.inclination_ref_side, ridge.angle_opp_edge_end) == (45.0, 90.0)

    saw = SawCut(start_x=1.0, start_y=2.0, start_depth=3.0, length=4.0, depth=5.0, machining_limits=SawCutMachiningLimits(False), tool_position="center").scaled(10.0)
    assert (saw.start_x, saw.start_y, saw.start_depth, saw.length, saw.depth) == (10.0, 20.0, 30.0, 40.0, 50.0)
    assert (saw.angle, saw.inclination, saw.bevel, saw.tool_position) == (90.0, 90.0, 0.0, "center")
    assert saw.machining_limits.face_limited_start is False

    triangle = TriangleCut(start_x=1.0, start_y=2.0, start_depth=3.0, normal_1_y=0.5).scaled(10.0)
    assert (triangle.start_x, triangle.start_y, triangle.start_depth) == (10.0, 20.0, 30.0)
    assert (triangle.normal_1_x, triangle.normal_1_y) == (1.0, 0.5)

    chamfer = Chamfer(start_x=1.0, length=2.0, depth=3.0).scaled(10.0)
    assert (chamfer.start_x, chamfer.length, chamfer.depth) == (10.0, 20.0, 30.0)

    planing = Planing(start_x=1.0, length=2.0, depth=3.0).scaled(10.0)
    assert (planing.start_x, planing.length, planing.depth) == (10.0, 20.0, 30.0)

    sphere = Sphere(start_x=1.0, start_y=2.0, start_depth=3.0, length=4.0, radius=5.0, start_offset=6.0).scaled(10.0)
    assert (sphere.start_x, sphere.start_y, sphere.start_depth, sphere.length, sphere.radius, sphere.start_offset) == (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)

    marking = Marking(start_x=1.0, start_y=2.0, angle=3.0, length=4.0, width=5.0).scaled(10.0)
    assert (marking.start_x, marking.start_y, marking.length, marking.width) == (10.0, 20.0, 40.0, 50.0)
    assert (marking.angle, marking.interior_angle) == (3.0, 90.0)


def test_json_round_trip():
    header = {"priority": 0, "process_id": 0}
    assert_serializes(
        RidgeValleyCut(start_x=5.0, length=20.0, ref_side_index=2),
        dict(
            header,
            ref_side_index=2,
            start_x=5.0,
            start_y=50.0,
            start_depth=0.0,
            inclination_ref_side=45.0,
            inclination_opp_side=45.0,
            start_limited=False,
            end_limited=False,
            length=20.0,
            angle_ref_edge_start=90.0,
            angle_ref_edge_end=90.0,
            angle_opp_edge_start=90.0,
            angle_opp_edge_end=90.0,
        ),
    )
    assert_serializes(
        SawCut(depth=20.0, machining_limits=SawCutMachiningLimits(face_limited_bottom=False), tool_position="right"),
        dict(
            header,
            ref_side_index=0,
            start_x=0.0,
            start_y=0.0,
            start_depth=0.0,
            angle=90.0,
            inclination=90.0,
            bevel=0.0,
            length=100.0,
            depth=20.0,
            machining_limits={"FaceLimitedStart": True, "FaceLimitedEnd": True, "FaceLimitedBottom": False},
            tool_position="right",
        ),
    )
    assert_serializes(
        TriangleCut(),
        dict(
            header,
            ref_side_index=0,
            start_x=0.0,
            start_y=60.0,
            start_depth=60.0,
            normal_1_x=1.0,
            normal_1_y=0.0,
            normal_1_z=0.0,
            normal_2_x=1.0,
            normal_2_y=0.0,
            normal_2_z=0.0,
        ),
    )
    assert_serializes(
        Chamfer(chamfer_edge_41=False),
        dict(
            header,
            ref_side_index=0,
            start_x=0.0,
            start_limited=False,
            end_limited=False,
            length=0.0,
            depth=1.0,
            chamfer_edge_12=True,
            chamfer_edge_23=True,
            chamfer_edge_34=True,
            chamfer_edge_41=False,
            chamfer_exit="orthogonal",
        ),
    )
    assert_serializes(
        Planing(plane_side_2=False),
        dict(
            header,
            ref_side_index=0,
            start_x=0.0,
            length=0.0,
            depth=1.0,
            start_limited=False,
            end_limited=False,
            plane_side_1=True,
            plane_side_2=False,
            plane_side_3=True,
            plane_side_4=True,
        ),
    )
    assert_serializes(
        Sphere(orientation="end"),
        dict(header, ref_side_index=0, orientation="end", start_x=0.0, start_y=60.0, start_depth=60.0, length=50.0, radius=50.0, start_offset=0.0),
    )
    assert_serializes(
        Marking(style="double"),
        dict(header, ref_side_index=0, start_x=0.0, start_y=0.0, angle=0.0, length_limited=False, length=20.0, width=100.0, interior_angle=90.0, style="double"),
    )


def test_btlx_round_trip():
    processings = [
        RidgeValleyCut(start_y=30.0, inclination_opp_side=-20.0, start_limited=True, length=100.0, ref_side_index=1),
        SawCut(start_x=10.0, machining_limits=SawCutMachiningLimits(face_limited_end=False), tool_position="right"),
        TriangleCut(start_x=500.0, normal_1_z=1.0),
        Chamfer(depth=5.0, chamfer_edge_23=False, chamfer_exit="round", start_limited=True),
        Planing(depth=3.0, plane_side_2=False),
        Sphere(orientation="end", radius=30.0, ref_side_index=2),
        Marking(style="square", length_limited=True, ref_side_index=3),
    ]
    beam = make_beam()
    beam.add_features(processings)
    model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    model.add_element(beam)

    reader = BTLxReader()
    features = list(reader.xml_to_model(BTLxWriter().model_to_xml(model)).elements())[0].features

    assert not reader.errors
    assert [type(feature) for feature in features] == [type(processing) for processing in processings]
    assert [feature.__data__ for feature in features] == [processing.__data__ for processing in processings]


@pytest.mark.requires_occ
class TestRidgeValleyCut:
    @pytest.mark.parametrize(
        "ref_side_index, side_width, side_height",
        [(0, WIDTH, HEIGHT), (1, HEIGHT, WIDTH), (2, WIDTH, HEIGHT), (3, HEIGHT, WIDTH)],
    )
    def test_ridge_through_the_element(self, ref_side_index, side_width, side_height):
        processing = RidgeValleyCut(start_y=30.0, inclination_ref_side=20.0, inclination_opp_side=20.0, ref_side_index=ref_side_index)
        beam, geometry = cut(processing)

        opp_width = side_width - 30.0
        assert BEAM_VOLUME - geometry.volume == pytest.approx(LENGTH * math.tan(math.radians(20.0)) * (30.0**2 + opp_width**2) / 2.0)
        assert is_solid(beam, geometry, ref_side_index, 500.0, 30.0, -1.0)
        assert not is_solid(beam, geometry, ref_side_index, 500.0, 2.0, -1.0)
        assert not is_solid(beam, geometry, ref_side_index, 500.0, side_width - 2.0, -1.0)
        assert is_solid(beam, geometry, ref_side_index, 500.0, 2.0, -side_height + 1.0)

    def test_inclinations_belong_to_their_sides(self):
        # the steep plane on the reference edge's side drops 30 * tan(60)
        processing = RidgeValleyCut(start_y=30.0, inclination_ref_side=60.0, inclination_opp_side=0.0, start_depth=10.0)
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(LENGTH * (WIDTH * 10.0 + 30.0**2 * math.tan(math.radians(60.0)) / 2.0))
        assert not is_solid(beam, geometry, 0, 500.0, 1.0, -55.0)
        assert is_solid(beam, geometry, 0, 500.0, 99.0, -11.0)

    def test_valley(self):
        processing = RidgeValleyCut(start_depth=50.0, inclination_ref_side=-45.0, inclination_opp_side=-45.0)
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(LENGTH * 50.0**2)
        assert not is_solid(beam, geometry, 0, 500.0, 50.0, -49.0)
        assert is_solid(beam, geometry, 0, 500.0, 1.0, -2.0)
        assert is_solid(beam, geometry, 0, 500.0, 50.0, -51.0)

    @pytest.mark.parametrize(
        "start_limited, end_limited, expected_length, solid_x, cut_x",
        [
            (True, True, 300.0, (150.0, 550.0), (250.0,)),
            (False, True, 500.0, (550.0,), (150.0, 250.0)),
            (True, False, 800.0, (150.0,), (250.0, 550.0)),
            (False, False, LENGTH, (), (150.0, 250.0, 550.0)),
        ],
    )
    def test_limits(self, start_limited, end_limited, expected_length, solid_x, cut_x):
        processing = RidgeValleyCut(start_x=200.0, length=300.0, start_limited=start_limited, end_limited=end_limited)
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(expected_length * 50.0**2)
        assert all(is_solid(beam, geometry, 0, x, 2.0, -1.0) for x in solid_x)
        assert not any(is_solid(beam, geometry, 0, x, 2.0, -1.0) for x in cut_x)

    def test_edge_angles_are_interior_angles_of_their_side(self):
        # a flat pocket: the limits are lines in the plane parallel to the side, each trapezoid corner adds or takes 50 * 50 / 2
        processing = RidgeValleyCut(
            start_x=100.0,
            length=300.0,
            start_depth=20.0,
            inclination_ref_side=0.0,
            inclination_opp_side=0.0,
            start_limited=True,
            end_limited=True,
            angle_ref_edge_start=45.0,
            angle_opp_edge_end=135.0,
        )
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(20.0 * 300.0 * WIDTH)
        assert is_solid(beam, geometry, 0, 110.0, 5.0, -10.0)
        assert not is_solid(beam, geometry, 0, 110.0, 45.0, -10.0)
        assert not is_solid(beam, geometry, 0, 110.0, 55.0, -10.0)
        assert not is_solid(beam, geometry, 0, 410.0, 95.0, -10.0)
        assert is_solid(beam, geometry, 0, 410.0, 55.0, -10.0)

    def test_limiting_walls_stand_on_the_inclined_plane(self):
        processing = RidgeValleyCut(start_x=100.0, start_limited=True, angle_ref_edge_start=45.0)
        beam, geometry = cut(processing)

        # a point on the wall: along the limiting line in the inclined plane, then up from that plane
        along = Vector(0.5**0.5, -0.5, -0.5)
        up = Vector(0.0, -(0.5**0.5), 0.5**0.5)
        wall_normal = Vector(0.5**0.5, 0.5, 0.5)
        on_wall = Point(100.0, 50.0, 0.0) + along * 30.0 + up * 5.0
        assert not is_solid(beam, geometry, 0, *(on_wall + wall_normal))
        assert is_solid(beam, geometry, 0, *(on_wall - wall_normal))

    def test_oriented_element(self):
        processing = RidgeValleyCut(start_y=30.0, inclination_ref_side=20.0, inclination_opp_side=20.0, ref_side_index=1)
        assert removed(processing, ROTATED_FRAME) == pytest.approx(LENGTH * math.tan(math.radians(20.0)) * (30.0**2 + 170.0**2) / 2.0)


@pytest.mark.requires_occ
class TestSawCut:
    KERF = 2.0  # of the 100 wide beam

    @pytest.mark.parametrize(
        "tool_position, solid_x, cut_x",
        [("left", 500.5, 499.5), ("right", 499.5, 500.5)],
    )
    def test_tool_position_along_the_default_direction(self, tool_position, solid_x, cut_x):
        beam, geometry = cut(SawCut(start_x=500.0, start_y=20.0, length=50.0, depth=30.0, tool_position=tool_position))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(50.0 * 30.0 * self.KERF)
        assert not is_solid(beam, geometry, 0, cut_x, 40.0, -10.0)
        assert is_solid(beam, geometry, 0, solid_x, 40.0, -10.0)
        # stops at both ends of the cut, and at its depth
        assert is_solid(beam, geometry, 0, cut_x, 19.0, -10.0)
        assert is_solid(beam, geometry, 0, cut_x, 71.0, -10.0)
        assert is_solid(beam, geometry, 0, cut_x, 40.0, -31.0)

    def test_center_tool_position(self):
        beam, geometry = cut(SawCut(start_x=500.0, start_y=20.0, length=50.0, depth=30.0, tool_position="center"))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(50.0 * 30.0 * self.KERF)
        assert not is_solid(beam, geometry, 0, 500.9, 40.0, -10.0)
        assert not is_solid(beam, geometry, 0, 499.1, 40.0, -10.0)

    @pytest.mark.parametrize(
        "angle, solid_points, cut_points",
        [
            (0.0, [(601.0, 49.5), (549.0, 49.5)], [(590.0, 49.5), (560.0, 49.5)]),  # along -X, left of it is -Y
            (180.0, [(599.0, 50.5), (651.0, 50.5)], [(610.0, 50.5), (640.0, 50.5)]),  # along +X, left of it is +Y
            (-90.0, [(600.5, 51.0), (600.5, 9.0)], [(600.5, 40.0), (600.5, 20.0)]),  # along -Y, left of it is +X
        ],
    )
    def test_angle_is_measured_from_the_negative_x_axis(self, angle, solid_points, cut_points):
        beam, geometry = cut(SawCut(start_x=600.0, start_y=50.0, angle=angle, length=40.0 if angle == -90.0 else 50.0, depth=30.0))

        assert not any(is_solid(beam, geometry, 0, x, y, -10.0) for x, y in cut_points)
        assert all(is_solid(beam, geometry, 0, x, y, -10.0) for x, y in solid_points)

    def test_start_depth(self):
        beam, geometry = cut(SawCut(start_x=500.0, start_y=20.0, start_depth=10.0, length=50.0, depth=30.0))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(50.0 * 30.0 * self.KERF)
        assert is_solid(beam, geometry, 0, 499.5, 40.0, -9.0)
        assert not is_solid(beam, geometry, 0, 499.5, 40.0, -39.0)
        assert is_solid(beam, geometry, 0, 499.5, 40.0, -41.0)

    def test_inclination_leans_to_the_left_of_the_cut(self):
        beam, geometry = cut(SawCut(start_x=500.0, start_y=20.0, start_depth=10.0, inclination=45.0, length=50.0, depth=30.0))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(50.0 * 30.0 * math.sqrt(2.0) * self.KERF)
        assert not is_solid(beam, geometry, 0, 479.5, 40.0, -30.0)  # the saw plane is at 480 at this depth
        assert is_solid(beam, geometry, 0, 480.5, 40.0, -30.0)

    def test_bevel_deepens_the_end_of_the_cut(self):
        beam, geometry = cut(SawCut(start_x=500.0, start_y=20.0, bevel=45.0, length=50.0, depth=30.0))

        assert BEAM_VOLUME - geometry.volume == pytest.approx((50.0 * 30.0 + 50.0**2 / 2.0) * self.KERF)
        assert not is_solid(beam, geometry, 0, 499.5, 65.0, -70.0)
        assert is_solid(beam, geometry, 0, 499.5, 25.0, -70.0)

    @pytest.mark.parametrize(
        "limits, expected_length, expected_depth",
        [
            (SawCutMachiningLimits(face_limited_start=False), 70.0, 30.0),
            (SawCutMachiningLimits(face_limited_end=False), 80.0, 30.0),
            (SawCutMachiningLimits(face_limited_bottom=False), 50.0, HEIGHT),
            ({"FaceLimitedStart": "no", "FaceLimitedEnd": "no", "FaceLimitedBottom": "yes"}, WIDTH, 30.0),
        ],
    )
    def test_machining_limits(self, limits, expected_length, expected_depth):
        processing = SawCut(start_x=500.0, start_y=20.0, length=50.0, depth=30.0, machining_limits=limits)
        assert removed(processing) == pytest.approx(expected_length * expected_depth * self.KERF)

    def test_from_line_and_element(self):
        beam = make_beam(ROTATED_FRAME)
        ref_side = beam.ref_sides[1]
        line = Line(ref_side.to_world_coordinates(Point(500.0, 20.0, -5.0)), ref_side.to_world_coordinates(Point(470.0, 60.0, -5.0)))

        processing = SawCut.from_shapes_and_element(line, beam, 30.0, ref_side_index=1, tool_position="center")

        assert processing.ref_side_index == 1
        assert processing.tool_position == "center"
        assert (processing.start_x, processing.start_y, processing.start_depth, processing.depth) == pytest.approx((500.0, 20.0, 5.0, 30.0))
        assert processing.length == pytest.approx(50.0)
        assert processing.angle == pytest.approx(math.degrees(math.atan2(40.0, 30.0)))
        assert removed(processing, ROTATED_FRAME) == pytest.approx(50.0 * 30.0 * self.KERF)


@pytest.mark.requires_occ
class TestTriangleCut:
    def test_notch_lies_on_the_positive_side_of_both_normals(self):
        beam, geometry = cut(TriangleCut(start_x=500.0, start_y=50.0, start_depth=100.0, normal_1_x=1.0, normal_1_z=1.0, normal_2_x=-1.0, normal_2_z=1.0))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(100.0 * 200.0 / 2.0 * WIDTH)
        assert not is_solid(beam, geometry, 0, 500.0, 50.0, -99.0)
        assert is_solid(beam, geometry, 0, 500.0, 50.0, -101.0)
        assert is_solid(beam, geometry, 0, 390.0, 50.0, -1.0)
        assert is_solid(beam, geometry, 0, 610.0, 50.0, -1.0)

    def test_normals_need_no_unit_length(self):
        processing = TriangleCut(start_x=500.0, start_y=50.0, start_depth=100.0, normal_1_x=3.0, normal_1_z=3.0, normal_2_x=-0.5, normal_2_z=0.5)
        assert removed(processing) == pytest.approx(100.0 * 200.0 / 2.0 * WIDTH)

    def test_corner_cut(self):
        # the planes of the figure: the corner of the opposite edge and the end of the element goes
        beam, geometry = cut(TriangleCut(start_x=900.0, start_y=50.0, start_depth=0.0, normal_1_x=1.0, normal_2_y=1.0, normal_1_y=0.0, normal_2_x=0.0, ref_side_index=2))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(100.0 * 50.0 * HEIGHT)
        assert not is_solid(beam, geometry, 2, 950.0, 75.0, -100.0)
        assert is_solid(beam, geometry, 2, 950.0, 25.0, -100.0)
        assert is_solid(beam, geometry, 2, 850.0, 75.0, -100.0)

    def test_identical_normals_cut_a_half_space(self):
        beam, geometry = cut(TriangleCut(start_x=300.0))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(700.0 * WIDTH * HEIGHT)
        assert is_solid(beam, geometry, 0, 299.0, 50.0, -100.0)

    def test_zero_normal_is_reported(self):
        beam = make_beam()
        beam.add_features([TriangleCut(normal_1_x=0.0)])
        beam.compute_elementgeometry(include_features=True)
        assert beam.debug_info

    def test_from_planes_and_element(self):
        beam = make_beam(ROTATED_FRAME)
        ref_side = beam.ref_sides[3]
        point = ref_side.to_world_coordinates(Point(500.0, 50.0, -50.0))
        normal_1 = ref_side.to_world_coordinates(Vector(1.0, 0.0, 1.0))
        normal_2 = ref_side.to_world_coordinates(Vector(-1.0, 0.0, 1.0))

        processing = TriangleCut.from_shapes_and_element(Plane(point, normal_1), Plane(point, normal_2), beam, ref_side_index=3)

        assert processing.ref_side_index == 3
        assert (processing.start_x, processing.start_depth) == pytest.approx((500.0, 50.0))
        assert (processing.normal_1_x, processing.normal_1_y, processing.normal_1_z) == pytest.approx((0.5**0.5, 0.0, 0.5**0.5))
        assert (processing.normal_2_x, processing.normal_2_y, processing.normal_2_z) == pytest.approx((-(0.5**0.5), 0.0, 0.5**0.5))
        assert removed(processing, ROTATED_FRAME) == pytest.approx(50.0 * 100.0 / 2.0 * HEIGHT)

    def test_parallel_planes_are_rejected(self):
        with pytest.raises(ValueError):
            TriangleCut.from_planes_and_element((Plane([0, 0, 0], [1, 0, 0]), Plane([10, 0, 0], [1, 0, 0])), make_beam())


@pytest.mark.requires_occ
class TestChamfer:
    @pytest.mark.parametrize(
        "edge, ref_side_index",
        [("chamfer_edge_12", 0), ("chamfer_edge_23", 1), ("chamfer_edge_34", 2), ("chamfer_edge_41", 3)],
    )
    def test_each_edge(self, edge, ref_side_index):
        edges = {"chamfer_edge_12": False, "chamfer_edge_23": False, "chamfer_edge_34": False, "chamfer_edge_41": False}
        edges[edge] = True
        beam, geometry = cut(Chamfer(depth=10.0, **edges))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(10.0**2 / 2.0 * LENGTH)
        # the edge is the reference edge of this side, the next one is its opposite edge
        assert not is_solid(beam, geometry, ref_side_index, 500.0, 2.0, -2.0)
        assert is_solid(beam, geometry, ref_side_index, 500.0, 6.0, -6.0)
        width = beam.get_dimensions_relative_to_side(ref_side_index)[0]
        assert is_solid(beam, geometry, ref_side_index, 500.0, width - 2.0, -2.0)

    def test_all_edges(self):
        assert removed(Chamfer(depth=10.0), ROTATED_FRAME) == pytest.approx(4.0 * 10.0**2 / 2.0 * LENGTH)

    @pytest.mark.parametrize(
        "start_limited, end_limited, expected_length, solid_x, cut_x",
        [
            (True, True, 300.0, (99.0, 401.0), (101.0, 399.0)),
            (False, True, 400.0, (401.0,), (99.0, 399.0)),
            (True, False, 900.0, (99.0,), (101.0, 401.0)),
        ],
    )
    def test_limits(self, start_limited, end_limited, expected_length, solid_x, cut_x):
        processing = Chamfer(
            depth=10.0, start_x=100.0, length=300.0, start_limited=start_limited, end_limited=end_limited, chamfer_edge_23=False, chamfer_edge_34=False, chamfer_edge_41=False
        )
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(10.0**2 / 2.0 * expected_length)
        assert all(is_solid(beam, geometry, 0, x, 1.0, -1.0) for x in solid_x)
        assert not any(is_solid(beam, geometry, 0, x, 1.0, -1.0) for x in cut_x)

    @pytest.mark.parametrize(
        "chamfer_exit, exit_volume_ratio, relative_tolerance",
        [(ChamferExitType.ANGULAR, 1.0 / 3.0, 1e-6), (ChamferExitType.ROUND, 2.0 / 3.0, 1e-3)],
    )
    def test_exits(self, chamfer_exit, exit_volume_ratio, relative_tolerance):
        # an exit has the height of the chamfer as its length, its sections are triangles of area height(x)^2
        height = 10.0 / math.sqrt(2.0)
        expected = (300.0 - 2.0 * height) * height**2 + 2.0 * exit_volume_ratio * height**3
        processing = Chamfer(
            depth=10.0,
            start_x=100.0,
            length=300.0,
            start_limited=True,
            end_limited=True,
            chamfer_edge_23=False,
            chamfer_edge_34=False,
            chamfer_edge_41=False,
            chamfer_exit=chamfer_exit,
        )
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(expected, rel=relative_tolerance)
        assert is_solid(beam, geometry, 0, 100.5, 2.5, -2.5)
        assert not is_solid(beam, geometry, 0, 110.0, 2.5, -2.5)
        assert is_solid(beam, geometry, 0, 399.5, 2.5, -2.5)
        assert not is_solid(beam, geometry, 0, 390.0, 2.5, -2.5)

    def test_too_short_for_exits_is_reported(self):
        beam = make_beam()
        beam.add_features([Chamfer(depth=10.0, length=5.0, start_x=100.0, start_limited=True, end_limited=True, chamfer_exit=ChamferExitType.ANGULAR)])
        beam.compute_elementgeometry(include_features=True)
        assert beam.debug_info


@pytest.mark.requires_occ
class TestPlaning:
    @pytest.mark.parametrize("side", [1, 2, 3, 4])
    def test_each_side(self, side):
        sides = {"plane_side_1": False, "plane_side_2": False, "plane_side_3": False, "plane_side_4": False}
        sides["plane_side_{}".format(side)] = True
        beam, geometry = cut(Planing(depth=5.0, **sides))

        width, height = beam.get_dimensions_relative_to_side(side - 1)
        assert BEAM_VOLUME - geometry.volume == pytest.approx(5.0 * width * LENGTH)
        assert not is_solid(beam, geometry, side - 1, 500.0, width / 2.0, -4.0)
        assert is_solid(beam, geometry, side - 1, 500.0, width / 2.0, -6.0)
        assert is_solid(beam, geometry, side - 1, 500.0, width / 2.0, -height + 1.0)

    def test_all_sides(self):
        assert removed(Planing(depth=5.0), ROTATED_FRAME) == pytest.approx((WIDTH * HEIGHT - (WIDTH - 10.0) * (HEIGHT - 10.0)) * LENGTH)

    @pytest.mark.parametrize(
        "start_limited, end_limited, expected_length, solid_x, cut_x",
        [
            (True, True, 300.0, (99.0, 401.0), (101.0, 399.0)),
            (False, True, 400.0, (401.0,), (99.0, 399.0)),
            (True, False, 900.0, (99.0,), (101.0, 401.0)),
        ],
    )
    def test_limits(self, start_limited, end_limited, expected_length, solid_x, cut_x):
        processing = Planing(
            depth=5.0, start_x=100.0, length=300.0, start_limited=start_limited, end_limited=end_limited, plane_side_2=False, plane_side_3=False, plane_side_4=False
        )
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(5.0 * WIDTH * expected_length)
        assert all(is_solid(beam, geometry, 0, x, 50.0, -1.0) for x in solid_x)
        assert not any(is_solid(beam, geometry, 0, x, 50.0, -1.0) for x in cut_x)


def circle_in_rectangle_area(radius, half_x, half_y):
    """Area of a centered circle clipped by a centered rectangle."""

    def half_height(x):
        return min(half_y, math.sqrt(max(radius**2 - x**2, 0.0)))

    steps = 400
    width = min(radius, half_x)
    return 4.0 * sum(half_height((i + 0.5) * width / steps) for i in range(steps)) * width / steps


def sphere_removed_volume(center_x, radius, section_start, section_end):
    """Removed volume of a sphere centered in the beam, integrating over the sections along the beam."""
    near_radius = math.sqrt(radius**2 - (section_start - center_x) ** 2)
    far_radius = math.sqrt(radius**2 - (section_end - center_x) ** 2)

    def kept_radius(x):
        if x < section_start:
            return near_radius + section_start - x
        if x > section_end:
            return far_radius + x - section_end
        return math.sqrt(radius**2 - (x - center_x) ** 2)

    steps = 2000
    step = LENGTH / steps
    kept = sum(circle_in_rectangle_area(kept_radius((i + 0.5) * step), WIDTH / 2.0, HEIGHT / 2.0) * step for i in range(steps))
    return BEAM_VOLUME - kept


@pytest.mark.requires_occ
class TestSphere:
    def test_start_orientation(self):
        beam, geometry = cut(Sphere(start_x=400.0, start_y=50.0, start_depth=100.0, radius=40.0, length=60.0, start_offset=10.0))

        assert BEAM_VOLUME - geometry.volume == pytest.approx(sphere_removed_volume(440.0, 40.0, 410.0, 470.0), rel=1e-3)
        assert is_solid(beam, geometry, 0, 440.0, 50.0 + 39.0, -100.0)
        assert not is_solid(beam, geometry, 0, 440.0, 50.0 + 41.0, -100.0)
        assert not is_solid(beam, geometry, 0, 440.0, 50.0, -100.0 + 41.0)

    def test_end_orientation_mirrors_at_the_start_point(self):
        processing = Sphere(orientation="end", start_x=400.0, start_y=50.0, start_depth=100.0, radius=40.0, length=60.0, start_offset=10.0)
        beam, geometry = cut(processing)

        assert BEAM_VOLUME - geometry.volume == pytest.approx(sphere_removed_volume(360.0, 40.0, 330.0, 390.0), rel=1e-3)
        assert is_solid(beam, geometry, 0, 360.0, 50.0 + 39.0, -100.0)
        assert not is_solid(beam, geometry, 0, 360.0, 50.0 + 41.0, -100.0)
        assert is_solid(beam, geometry, 0, 440.0, 50.0 + 45.0, -100.0)

    def test_section_offset_is_kept_as_a_cone(self):
        # past the end of the section its circle widens at 45 degrees, instead of following the sphere
        beam, geometry = cut(Sphere(start_x=400.0, start_y=50.0, start_depth=100.0, radius=40.0, length=54.0, start_offset=2.0))

        section_end_radius = math.sqrt(40.0**2 - (456.0 - 440.0) ** 2)
        assert is_solid(beam, geometry, 0, 470.0, 50.0, -100.0 + section_end_radius + 13.0)
        assert not is_solid(beam, geometry, 0, 470.0, 50.0, -100.0 + section_end_radius + 15.0)

    def test_position_on_another_side(self):
        # from side 2, whose Y runs along the height, against the direction of the part's Y
        processing = Sphere(start_x=400.0, start_y=150.0, start_depth=60.0, radius=30.0, length=40.0, start_offset=10.0, ref_side_index=1)
        beam, geometry = cut(processing)

        assert is_solid(beam, geometry, 1, 430.0, 150.0 + 29.0, -60.0)
        assert not is_solid(beam, geometry, 1, 430.0, 150.0 + 31.0, -60.0)
        assert not is_solid(beam, geometry, 1, 430.0, 150.0 - 31.0, -60.0)
        assert BEAM_VOLUME - geometry.volume > 0.0

    def test_section_beyond_the_sphere_is_reported(self):
        beam = make_beam()
        beam.add_features([Sphere(radius=40.0, length=70.0, start_offset=20.0, start_x=400.0)])
        beam.compute_elementgeometry(include_features=True)
        assert beam.debug_info

    def test_from_sphere_and_element(self):
        beam = make_beam(ROTATED_FRAME)
        ref_side = beam.ref_sides[1]
        center = ref_side.to_world_coordinates(Point(400.0, 100.0, -50.0))

        processing = Sphere.from_shapes_and_element(SphereGeometry(30.0, point=center), beam, ref_side_index=1)

        assert processing.ref_side_index == 1
        assert (processing.start_x, processing.start_y, processing.start_depth) == pytest.approx((370.0, 100.0, 50.0))
        assert (processing.length, processing.radius, processing.start_offset) == pytest.approx((60.0, 30.0, 0.0))


@pytest.mark.requires_occ
@pytest.mark.parametrize("processing", [SawCut(length=0.0), Planing(start_limited=True, end_limited=True)])
def test_zero_length_removes_nothing(processing):
    assert removed(processing) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.requires_occ
def test_marking_leaves_the_geometry_unchanged():
    assert removed(Marking(start_x=100.0, style=MarkingStyleType.SQUARE)) == pytest.approx(0.0, abs=1e-6)


def test_marking_from_line_and_element():
    beam = make_beam(ROTATED_FRAME)
    ref_side = beam.ref_sides[2]
    line = Line(ref_side.to_world_coordinates(Point(100.0, 10.0, 0.0)), ref_side.to_world_coordinates(Point(70.0, 50.0, 0.0)))

    marking = Marking.from_shapes_and_element(line, beam, ref_side_index=2)

    assert marking.ref_side_index == 2
    assert marking.length_limited is True
    assert (marking.start_x, marking.start_y, marking.length) == pytest.approx((100.0, 10.0, 50.0))
    assert marking.angle == pytest.approx(math.degrees(math.atan2(40.0, 30.0)))


def test_sphere_splitting_the_element_keeps_the_largest_piece():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_feature(Sphere(start_x=100.0, start_y=50.0, start_depth=60.0, length=50.0, radius=50.0, start_offset=0.0))

    geometry = beam.compute_elementgeometry(include_features=True)

    assert not beam.debug_info
    assert geometry.volume > 0.8 * 1000.0 * 100.0 * 200.0


def test_failure_to_generate_a_volume_is_reported_on_the_element(mocker):
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    processing = Sphere(start_x=100.0)
    mocker.patch.object(Sphere, "volumes_from_params_and_element", side_effect=TypeError("No idea what to do with a: BrepFace"))
    beam.add_feature(processing)

    geometry = beam.compute_elementgeometry(include_features=True)

    assert len(beam.debug_info) == 1
    assert geometry.volume == pytest.approx(1000.0 * 100.0 * 200.0)

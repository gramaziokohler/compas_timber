import math

import pytest

from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import distance_point_point

from compas_timber.elements import Beam
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Tenon
from compas_timber.fabrication import OrientationType
from compas_timber.fabrication import TenonShapeType

from compas.tolerance import Tolerance


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


@pytest.fixture
def cross_beam():
    section = [60, 100]
    centerline = Line(Point(x=30782.4296640, y=-3257.66821289, z=0.0), Point(x=33782.4296640, y=-3257.66821289, z=0.0))
    return Beam.from_centerline(centerline, section[0], section[1])


@pytest.fixture
def main_beams():
    widths = [80.0, 120.0]
    heights = [100.0, 80.0]

    centerlines = [
        Line(Point(x=33300.5452394, y=-3257.66821289, z=0.0), Point(x=33607.9516217, y=-4000.58982486, z=156.858089632)),
        Line(Point(x=31995.4509589, y=-1725.41351885, z=-819.665898454), Point(x=32282.4296640, y=-3257.66821289, z=0.0)),
    ]
    return [Beam.from_centerline(centerline, width, height) for centerline, width, height in zip(centerlines, widths, heights)]


TENON_CUTTING_FRAMES = [
    Frame(
        point=Point(x=30782.430, y=-3287.668, z=-50.000),
        xaxis=Vector(x=1.000, y=-0.000, z=0.000),
        yaxis=Vector(x=0.000, y=0.000, z=1.000),
    ),
    Frame(
        point=Point(x=30782.430, y=-3227.668, z=50.000),
        xaxis=Vector(x=1.000, y=-0.000, z=0.000),
        yaxis=Vector(x=0.000, y=-0.000, z=-1.000),
    ),
]

MORTISE_CUTTING_FRAMES = [
    Frame(
        point=Point(x=33267.5475182, y=-3287.66821289, z=-2.14751049418),
        xaxis=Vector(x=0.258819045103, y=2.74488004975e-17, z=-0.965925826289),
        yaxis=Vector(x=-0.965925826289, y=1.80834604553e-16, z=-0.258819045103),
    ),
    Frame(
        point=Point(x=32329.7761348, y=-3227.66821289, z=-18.8301288595),
        xaxis=Vector(x=0.104528463268, y=-1.03409422113e-16, z=-0.994521895368),
        yaxis=Vector(x=0.994521895368, y=-4.78555402447e-16, z=0.104528463268),
    ),
]

EXPECTED_TENON_PARAMS = [
    OrderedDict(
        [
            ("Name", "Tenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("Orientation", "start"),
            ("StartX", "14.413"),
            ("StartY", "45.000"),
            ("StartDepth", "-1.961"),
            ("Angle", "78.961"),
            ("Inclination", "67.521"),
            ("Rotation", "105.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "80.000"),
            ("Width", "30.000"),
            ("Height", "60.000"),
            ("Shape", "round"),
            ("ShapeRadius", "15.000"),
            ("Chamfer", "no"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Tenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "end"),
            ("StartX", "1734.105"),
            ("StartY", "47.000"),
            ("StartDepth", "7.940"),
            ("Angle", "62.265"),
            ("Inclination", "79.392"),
            ("Rotation", "96.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "110.000"),
            ("Width", "40.000"),
            ("Height", "60.000"),
            ("Shape", "round"),
            ("ShapeRadius", "20.000"),
            ("Chamfer", "no"),
        ]
    ),
]

EXPECTED_MORTISE_PARAMS = [
    OrderedDict(
        [
            ("Name", "Mortise"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("StartX", "2485.118"),
            ("StartY", "47.852"),
            ("StartDepth", "0.000"),
            ("Angle", "15.000"),
            ("Slope", "90.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "80.000"),
            ("Width", "30.000"),
            ("Depth", "60.000"),
            ("Shape", "round"),
            ("ShapeRadius", "15.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Mortise"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1547.346"),
            ("StartY", "68.830"),
            ("StartDepth", "0.000"),
            ("Angle", "174.000"),
            ("Slope", "90.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "110.000"),
            ("Width", "40.000"),
            ("Depth", "60.000"),
            ("Shape", "round"),
            ("ShapeRadius", "20.000"),
        ]
    ),
]


@pytest.mark.parametrize(
    "test_index, expected_tenon_params, tenon_cutting_frames, start_y, start_depth, rotation, length, width, height, shape, shape_radius, ref_side_index",
    [
        (
            0,
            EXPECTED_TENON_PARAMS,
            TENON_CUTTING_FRAMES,
            -5.0,
            -5.0,
            15.0,
            80.0,
            30.0,
            60.0,
            "round",
            5.0,
            3,
        ),  # main_beam_a
        (
            1,
            EXPECTED_TENON_PARAMS,
            TENON_CUTTING_FRAMES,
            -7.0,
            2,
            -6.0,
            110.0,
            40.0,
            60.0,
            "round",
            7.5,
            1,
        ),  # main_beam_b
    ],
)
def test_tenon_params(
    main_beams,
    test_index,
    expected_tenon_params,
    tenon_cutting_frames,
    start_y,
    start_depth,
    rotation,
    length,
    width,
    height,
    shape,
    shape_radius,
    ref_side_index,
):
    # Create the Tenon
    tenon = Tenon.from_plane_and_beam(
        plane=tenon_cutting_frames[test_index],
        beam=main_beams[test_index],
        start_y=start_y,
        start_depth=start_depth,
        rotation=rotation,
        length=length,
        width=width,
        height=height,
        shape=shape,
        shape_radius=shape_radius,
        ref_side_index=ref_side_index,
    )
    # Validate generated parameters
    generated_params = tenon.params.header_attributes
    generated_params.update(tenon.params.as_dict())
    for key, value in expected_tenon_params[test_index].items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "test_index, expected_mortise_params, mortise_cutting_frames, start_depth, length, width, depth, shape, shape_radius, ref_side_index",
    [
        (
            0,
            EXPECTED_MORTISE_PARAMS,
            MORTISE_CUTTING_FRAMES,
            0.0,
            80.0,
            30.0,
            60.0,
            "round",
            15.0,
            3,
        ),  # main_beam_a
        (
            1,
            EXPECTED_MORTISE_PARAMS,
            MORTISE_CUTTING_FRAMES,
            0.0,
            110.0,
            40.0,
            60.0,
            "round",
            20.0,
            1,
        ),  # main_beam_b
    ],
)
def test_mortise_params(
    cross_beam,
    mortise_cutting_frames,
    test_index,
    expected_mortise_params,
    start_depth,
    length,
    width,
    depth,
    shape,
    shape_radius,
    ref_side_index,
):
    # Create the mortise
    mortise = Mortise.from_frame_and_beam(
        mortise_cutting_frames[test_index],
        cross_beam,
        start_depth,
        length,
        width,
        depth,
        shape,
        shape_radius,
        ref_side_index,
    )

    # Validate generated parameters
    generated_params = mortise.params.header_attributes
    generated_params.update(mortise.params.as_dict())
    for key, value in expected_mortise_params[test_index].items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "test_index, expected_tenon_params, mortise_cutting_frames",
    [
        (0, EXPECTED_TENON_PARAMS, MORTISE_CUTTING_FRAMES),
        (1, EXPECTED_TENON_PARAMS, MORTISE_CUTTING_FRAMES),
    ],
)
def test_tenon_frame_from_params(
    tol,
    main_beams,
    test_index,
    expected_tenon_params,
    mortise_cutting_frames,
):
    # convert string values to the appropriate types (float, bool, etc.)
    def convert_value(value):
        if isinstance(value, str):
            # convert to float if the string represents a number, including negative numbers
            if value.replace(".", "", 1).replace("-", "", 1).isdigit():
                return float(value)
            # convert specific strings to booleans
            if value.lower() in ["yes", "no"]:
                return value.lower() == "yes"
        return value

    # convert the OrderedDict values to the expected types
    params = {key.lower(): convert_value(value) for key, value in expected_tenon_params[test_index].items()}

    # instantiate Tenon with unpacked parameters from the OrderedDict
    tenon = Tenon(
        orientation=params["orientation"],
        start_x=params["startx"],
        start_y=params["starty"],
        start_depth=params["startdepth"],
        angle=params["angle"],
        inclination=params["inclination"],
        rotation=params["rotation"],
        length_limited_top=params["lengthlimitedtop"],
        length_limited_bottom=params["lengthlimitedbottom"],
        length=params["length"],
        width=params["width"],
        height=params["height"],
        shape=params["shape"],
        shape_radius=params["shaperadius"],
        ref_side_index=int(params["referenceplaneid"] - 1),
    )

    # generate frame from the parameters
    generated_frame = tenon.frame_from_params_and_beam(main_beams[test_index])
    dx = distance_point_point(generated_frame.point, mortise_cutting_frames[test_index].point)

    assert tol.is_zero(dx)
    assert tol.is_close(generated_frame.normal.x, mortise_cutting_frames[test_index].normal.x)
    assert tol.is_close(generated_frame.normal.y, mortise_cutting_frames[test_index].normal.y)
    assert tol.is_close(generated_frame.normal.z, mortise_cutting_frames[test_index].normal.z)


def test_tenon_scaled():
    tenon = Tenon(
        orientation=OrientationType.START,
        start_x=10.0,
        start_y=20.0,
        start_depth=30.0,
        angle=40.0,
        inclination=50.0,
        rotation=60.0,
        length_limited_top=True,
        length_limited_bottom=True,
        length=70.0,
        width=80.0,
        height=90.0,
        shape=TenonShapeType.ROUND,
        shape_radius=100.0,
    )

    scaled = tenon.scaled(2.0)

    assert scaled.orientation == tenon.orientation
    assert scaled.start_x == tenon.start_x * 2.0
    assert scaled.start_y == tenon.start_y * 2.0
    assert scaled.start_depth == tenon.start_depth * 2.0
    assert scaled.angle == tenon.angle
    assert scaled.inclination == tenon.inclination
    assert scaled.rotation == tenon.rotation
    assert scaled.length_limited_top == tenon.length_limited_top
    assert scaled.length_limited_bottom == tenon.length_limited_bottom
    assert scaled.length == tenon.length * 2.0
    assert scaled.width == tenon.width * 2.0
    assert scaled.height == tenon.height * 2.0
    assert scaled.shape == tenon.shape
    assert scaled.shape_radius == tenon.shape_radius * 2.0


# =============================================================================
# Mortise Slope: the box rotates about the width edge through its start point
# =============================================================================


def _mortise_box(slope):
    beam = Beam(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=400.0, width=100.0, height=100.0)
    mortise = Mortise(start_x=200.0, start_y=50.0, angle=0.0, slope=slope, length=80.0, width=40.0, depth=30.0, shape=TenonShapeType.SQUARE, ref_side_index=0)
    frame = mortise.frame_from_params_and_beam(beam)
    vertices = [vertex.point for vertex in mortise.volume_from_params_and_beam(beam).vertices]
    return frame, vertices


def _centroid(points):
    return Point(*[sum(point[i] for point in points) / len(points) for i in range(3)])


def test_a_square_mortise_is_unchanged_by_slope_90():
    frame, vertices = _mortise_box(90.0)
    depths = sorted({round(-frame.normal.dot(point - frame.point), 6) for point in vertices})
    assert depths == [0.0, 30.0]


def test_slope_tilts_the_floor_and_swings_it_back_past_the_start():
    # BTLx: Slope = 90 - rotation about the width edge through the start point.
    # The floor is square to the tilted depth axis, and below 90 it leans back.
    frame, sloped = _mortise_box(80.0)
    floor = sorted(sloped, key=lambda point: frame.normal.dot(point - frame.point))[:4]
    a, b, c = floor[0], floor[1], floor[2]
    floor_normal = Vector.from_start_end(a, b).cross(Vector.from_start_end(a, c)).unitized()
    assert math.degrees(math.acos(abs(floor_normal.dot(frame.normal)))) == pytest.approx(10.0)
    # the length runs along -yaxis from the start, so "back past the start" is +yaxis
    assert max(frame.yaxis.dot(point - frame.point) for point in floor) == pytest.approx(30.0 * math.sin(math.radians(10.0)))


def test_a_sloped_mortise_cuts_a_tilted_floor():
    beam = Beam(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=400.0, width=100.0, height=100.0)
    before = beam.geometry.volume
    mortise = Mortise(start_x=200.0, start_y=50.0, angle=0.0, slope=80.0, length=80.0, width=40.0, depth=30.0, shape=TenonShapeType.SQUARE, ref_side_index=0)
    beam.add_feature(mortise)
    beam._geometry = None
    removed = before - beam.geometry.volume
    # In the plane of the slope the cut is a quadrilateral: hinge, floor at the
    # start, floor at the far end, and where the far wall meets the face again.
    length, width, depth, r = 80.0, 40.0, 30.0, math.radians(10.0)
    axis = (math.sin(r), -math.cos(r))  # depth axis, leaning back past the start (x is back, y is up)
    along = (-math.cos(r), -math.sin(r))  # toward the far end, square to the axis
    hinge = (0.0, 0.0)
    floor_start = (depth * axis[0], depth * axis[1])
    floor_end = (floor_start[0] + length * along[0], floor_start[1] + length * along[1])
    climb = -floor_end[1] / math.cos(r)
    at_face = (floor_end[0] - climb * axis[0], 0.0)
    corners = [hinge, floor_start, floor_end, at_face]
    area = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1])))
    assert removed == pytest.approx(width * area, rel=1e-6)

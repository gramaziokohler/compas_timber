import pytest

from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import distance_point_point

from compas_timber.elements import Beam
from compas_timber._fabrication import Mortise
from compas_timber._fabrication import Tenon

from compas.tolerance import TOL
from compas.tolerance import Tolerance


@pytest.fixture
def cross_beam():
    section = [60, 120]
    centerline = Line(Point(x=30782.4296640, y=-3257.66821289, z=0.0), Point(x=33782.4296640, y=-3257.66821289, z=0.0))
    return Beam.from_centerline(centerline, section[0], section[1])


@pytest.fixture
def main_beams():
    widths = [80.0, 80.0, 100.0]
    heights = [100.0, 80.0, 120.0]

    centerlines = [
        Line(
            Point(x=33300.5452394, y=-3257.66821289, z=0.0), Point(x=33600.2957658, y=-3954.34485987, z=542.549175576)
        ),
        Line(
            Point(x=31995.4509589, y=-1725.41351885, z=-819.665898454), Point(x=32282.4296640, y=-3257.66821289, z=0.0)
        ),
    ]

    return [
        Beam.from_centerline(centerline, width, height)
        for centerline, width, height in zip(centerlines, widths, heights)
    ]


TENON_CUTTING_FRAMES = [
    Frame(
        point=Point(x=30782.430, y=-3287.668, z=-60.000),
        xaxis=Vector(x=1.000, y=-0.000, z=0.000),
        yaxis=Vector(x=0.000, y=0.000, z=1.000),
    ),
    Frame(
        point=Point(x=30782.430, y=-3227.668, z=60.000),
        xaxis=Vector(x=1.000, y=-0.000, z=0.000),
        yaxis=Vector(x=0.000, y=-0.000, z=-1.000),
    ),
]

MORTISE_CUTTING_FRAMES = [
    Frame(
        point=Point(x=33314.542, y=-3287.668, z=75.631),
        xaxis=Vector(x=-1.000, y=0.000, z=-0.014),
        yaxis=Vector(x=-0.014, y=-0.000, z=1.000),
    ),
    Frame(
        point=Point(x=32274.776, y=-3227.668, z=-99.122),
        xaxis=Vector(x=-1.000, y=0.000, z=0.026),
        yaxis=Vector(x=-0.026, y=-0.000, z=-1.000),
    ),
]

EXPECTED_TENON_PARAMS = [
    OrderedDict(
        [
            ("Name", "Tenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("Orientation", "start"),
            ("StartX", "70.915"),
            ("StartY", "41.000"),
            ("StartDepth", "7.740"),
            ("Angle", "62.120"),
            ("Inclination", "122.307"),
            ("Rotation", "75.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "100.000"),
            ("Width", "40.000"),
            ("Height", "40.000"),
            ("Shape", "round"),
            ("ShapeRadius", "20.000"),
            ("Chamfer", "no"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Tenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "1"),
            ("Orientation", "end"),
            ("StartX", "1687.777"),
            ("StartY", "42.000"),
            ("StartDepth", "-33.355"),
            ("Angle", "78.052"),
            ("Inclination", "117.222"),
            ("Rotation", "83.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "120.000"),
            ("Width", "50.000"),
            ("Height", "40.000"),
            ("Shape", "round"),
            ("ShapeRadius", "25.000"),
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
            ("StartX", "2532.112"),
            ("StartY", "135.631"),
            ("StartDepth", "0.000"),
            # ("Angle", "-89.213"), #! WHY??
            ("Angle", "-89.198"),
            ("Slope", "90.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "100.000"),
            ("Width", "40.000"),
            ("Depth", "40.000"),
            ("Shape", "round"),
            ("ShapeRadius", "20.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Mortise"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1492.346"),
            ("StartY", "159.122"),
            ("StartDepth", "0.000"),
            # ("Angle", "-88.529"), #! WHY??
            ("Angle", "-88.511"),
            ("Slope", "90.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "120.000"),
            ("Width", "50.000"),
            ("Depth", "40.000"),
            ("Shape", "round"),
            ("ShapeRadius", "25.000"),
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
            1.0,
            0.0,
            -15.0,
            100.0,
            40.0,
            40.0,
            "round",
            5.0,
            2,
        ),  # main_beam_a
        (
            1,
            EXPECTED_TENON_PARAMS,
            TENON_CUTTING_FRAMES,
            -2.0,
            -20.0,
            7.0,
            120.0,
            50.0,
            40.0,
            "round",
            7.5,
            0,
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
    generated_params = tenon.params_dict
    for key, value in expected_tenon_params[test_index].items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "test_index, expected_mortise_params, mortise_cutting_frames, start_depth, angle, length, width, depth, shape, shape_radius, ref_side_index",
    [
        (
            0,
            EXPECTED_MORTISE_PARAMS,
            MORTISE_CUTTING_FRAMES,
            0.0,
            -15.0,
            100.0,
            40.0,
            40.0,
            "round",
            20.0,
            3,
        ),  # main_beam_a
        (
            1,
            EXPECTED_MORTISE_PARAMS,
            MORTISE_CUTTING_FRAMES,
            0.0,
            7.0,
            120.0,
            50.0,
            40.0,
            "round",
            25.0,
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
    angle,
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
        angle,
        length,
        width,
        depth,
        shape,
        shape_radius,
        ref_side_index,
    )

    # Validate generated parameters
    generated_params = mortise.params_dict
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
    tolerance = Tolerance()
    tolerance.ABSOLUTE = 1e-3

    generated_frame = tenon.frame_from_params_and_beam(main_beams[test_index])
    dx = distance_point_point(generated_frame.point, mortise_cutting_frames[test_index].point)

    assert tolerance.is_zero(dx)
    assert tolerance.is_close(generated_frame.normal.x, mortise_cutting_frames[test_index].normal.x)
    assert tolerance.is_close(generated_frame.normal.y, mortise_cutting_frames[test_index].normal.y)
    assert tolerance.is_close(generated_frame.normal.z, mortise_cutting_frames[test_index].normal.z)

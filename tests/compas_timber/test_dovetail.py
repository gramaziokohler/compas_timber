import pytest

from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Frame
from compas.geometry import Vector

from compas_timber.elements import Beam
from compas_timber._fabrication import DovetailMortise
from compas_timber._fabrication import DovetailTenon


@pytest.fixture
def cross_beams():
    widths = [60.0, 60.0, 80.0]
    heights = [120.0, 120.0, 100.0]

    centerlines = [
        Line(Point(x=33782.4296640, y=-3257.66821289, z=0.0), Point(x=30782.4296640, y=-3257.66821289, z=0.0)),
        Line(Point(x=30782.4296640, y=-3257.66821289, z=0.0), Point(x=33782.4296640, y=-3257.66821289, z=0.0)),
        Line(Point(x=30782.4296640, y=-3257.66821289, z=0.0), Point(x=33782.4296640, y=-3257.66821289, z=0.0)),
    ]

    return [
        Beam.from_centerline(centerline, width, height)
        for centerline, width, height in zip(centerlines, widths, heights)
    ]


@pytest.fixture
def main_beams():
    widths = [80.0, 80.0, 100.0]
    heights = [100.0, 80.0, 120.0]
    z_vectors = [Vector(x=0.000, y=0.51422, z=0.703021), Vector(x=0, y=0.272144, z=-0.926735), Vector.Zaxis()]

    centerlines = [
        Line(
            Point(x=31332.0787451, y=-3257.66821289, z=-23.3661907508),
            Point(x=31832.0787451, y=-3973.19330068, z=500.0),
        ),
        Line(
            Point(x=32930.7147438, y=-2542.14312510, z=200.0),
            Point(x=32730.7147438, y=-3257.66821289, z=-10.1206126384),
        ),
        Line(Point(x=32730.7147438, y=-2542.14312510, z=-10.0), Point(x=32730.7147438, y=-3257.66821289, z=-10.0)),
    ]

    return [
        Beam.from_centerline(centerline, width, height, z_vector)
        for centerline, width, height, z_vector in zip(centerlines, widths, heights, z_vectors)
    ]


TENON_CUTTING_FRAMES = [
    Frame(
        point=Point(x=31330.8001549, y=-3287.66821289, z=-50.9810872474),
        xaxis=Vector(x=0.939692620786, y=-4.74845031169e-16, z=-0.342020143326),
        yaxis=Vector(x=-0.342020143326, y=2.34059774926e-16, z=-0.939692620786),
    ),
    Frame(
        point=Point(x=32726.3841104, y=-3227.66821289, z=-32.5776239351),
        xaxis=Vector(x=-0.996194698092, y=5.64393952025e-16, z=0.0871557427477),
        yaxis=Vector(x=-0.0871557427477, y=-1.18522451263e-17, z=-0.996194698092),
    ),
    Frame(
        point=Point(x=32730.7147438, y=-3217.66821289, z=50.0),
        xaxis=Vector(x=1.0, y=-6.12303176911e-17, z=-6.12303176911e-17),
        yaxis=Vector(x=6.12303176911e-17, y=6.12303176911e-17, z=1.0),
    ),
]

EXPECTED_TENON_PARAMS = [
    OrderedDict(
        [
            ("Name", "DovetailTenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "1"),
            ("Orientation", "start"),
            ("StartX", "6.262"),
            ("StartY", "45.000"),
            ("StartDepth", "10.000"),
            ("Angle", "119.424"),
            ("Inclination", "53.817"),
            ("Rotation", "70.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "60.000"),
            ("Width", "45.000"),
            ("Height", "28.000"),
            ("ConeAngle", "10.000"),
            ("UseFlankAngle", "no"),
            ("FlankAngle", "15.000"),
            ("Shape", "radius"),
            ("ShapeRadius", "22.497"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DovetailTenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("Orientation", "end"),
            ("StartX", "751.524"),
            ("StartY", "50.000"),
            ("StartDepth", "10.000"),
            ("Angle", "105.013"),
            ("Inclination", "73.635"),
            ("Rotation", "85.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "57.653"),
            ("Width", "36.926"),
            ("Height", "28.000"),
            ("ConeAngle", "15.000"),
            ("UseFlankAngle", "no"),
            ("FlankAngle", "15.000"),
            ("Shape", "radius"),
            ("ShapeRadius", "22.497"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DovetailTenon"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("Orientation", "end"),
            ("StartX", "675.525"),
            ("StartY", "50.000"),
            ("StartDepth", "0.000"),
            ("Angle", "90.000"),
            ("Inclination", "90.000"),
            ("Rotation", "90.000"),
            ("LengthLimitedTop", "yes"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "80.000"),
            ("Width", "50.000"),
            ("Height", "28.000"),
            ("ConeAngle", "7.000"),
            ("UseFlankAngle", "no"),
            ("FlankAngle", "15.000"),
            ("Shape", "square"),
            ("ShapeRadius", "22.497"),
        ]
    ),
]

EXPECTED_MORTISE_PARAMS = [
    OrderedDict(
        [
            ("Name", "DovetailMortise"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "2451.630"),
            ("StartY", "110.981"),
            ("StartDepth", "0.000"),
            ("Angle", "-110.000"),
            ("Slope", "90.000"),
            ("LimitationTop", "unlimited"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "60.000"),
            ("Width", "45.000"),
            ("Depth", "28.000"),
            ("ConeAngle", "10.000"),
            ("UseFlankAngle", "no"),
            ("FlankAngle", "15.000"),
            ("Shape", "radius"),
            ("ShapeRadius", "22.497"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DovetailMortise"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1943.954"),
            ("StartY", "92.578"),
            ("StartDepth", "0.000"),
            ("Angle", "-85.000"),
            ("Slope", "90.000"),
            ("LimitationTop", "unlimited"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "57.653"),
            ("Width", "36.926"),
            ("Depth", "28.000"),
            ("ConeAngle", "15.000"),
            ("UseFlankAngle", "no"),
            ("FlankAngle", "15.000"),
            ("Shape", "radius"),
            ("ShapeRadius", "22.497"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DovetailMortise"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1948.285"),
            ("StartY", "0.000"),
            ("StartDepth", "0.000"),
            ("Angle", "90.000"),
            ("Slope", "90.000"),
            ("LimitationTop", "unlimited"),
            ("LengthLimitedBottom", "yes"),
            ("Length", "80.000"),
            ("Width", "50.000"),
            ("Depth", "28.000"),
            ("ConeAngle", "7.000"),
            ("UseFlankAngle", "no"),
            ("FlankAngle", "15.000"),
            ("Shape", "square"),
            ("ShapeRadius", "22.497"),
        ]
    ),
]


@pytest.mark.parametrize(
    "test_index, expected_tenon_params, cutting_plane_index, start_y, start_depth, rotation, length, width, height, cone_angle, flank_angle, shape, shape_radius, ref_side_index",
    [
        (
            0,
            EXPECTED_TENON_PARAMS[0],
            1,
            5.0,
            10.0,
            -20.0,
            60.0,
            45.0,
            28.0,
            10.0,
            15.0,
            "radius",
            22.497,
            0,
        ),  # main_beam_a
        (
            1,
            EXPECTED_TENON_PARAMS[1],
            1,
            -10.0,
            10.0,
            5.0,
            60.0,
            45.0,
            28.0,
            15.0,
            15.0,
            "radius",
            22.497,
            2,
        ),  # main_beam_b
        (
            2,
            EXPECTED_TENON_PARAMS[2],
            1,
            0.0,
            0.0,
            0.0,
            80.0,
            50.0,
            28.0,
            7.0,
            15.0,
            "square",
            22.497,
            2,
        ),  # main_beam_c
    ],
)
def test_dovetailtenon_params(
    main_beams,
    cross_beams,
    test_index,
    expected_tenon_params,
    cutting_plane_index,
    start_y,
    start_depth,
    rotation,
    length,
    width,
    height,
    cone_angle,
    flank_angle,
    shape,
    shape_radius,
    ref_side_index,
):
    # Create the DovetailTenon
    dovetail_tenon = DovetailTenon.from_plane_and_beam(
        plane=cross_beams[test_index].ref_sides[cutting_plane_index],
        beam=main_beams[test_index],
        start_y=start_y,
        start_depth=start_depth,
        rotation=rotation,
        length=length,
        width=width,
        height=height,
        cone_angle=cone_angle,
        flank_angle=flank_angle,
        shape=shape,
        shape_radius=shape_radius,
        ref_side_index=ref_side_index,
    )
    # Validate generated parameters
    generated_params = dovetail_tenon.params_dict
    for key, value in expected_tenon_params.items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "test_index, expected_mortise_params, cutting_frame, start_depth, angle, length, width, depth, cone_angle, flank_angle, shape, shape_radius, ref_side_index",
    [
        (
            0,
            EXPECTED_MORTISE_PARAMS[0],
            TENON_CUTTING_FRAMES[0],
            0.0,
            -20.0,
            60.0,
            45.0,
            28.0,
            10.0,
            15.0,
            "radius",
            22.497,
            1,
        ),  # main_beam_a
        (
            1,
            EXPECTED_MORTISE_PARAMS[1],
            TENON_CUTTING_FRAMES[1],
            0.0,
            5.0,
            57.65307084966669,
            36.925746566661111,
            28.0,
            15.0,
            15.0,
            "radius",
            22.497,
            1,
        ),  # main_beam_b
        (
            2,
            EXPECTED_MORTISE_PARAMS[2],
            TENON_CUTTING_FRAMES[2],
            0.0,
            0.0,
            80.0,
            50.0,
            28.0,
            7.0,
            15.0,
            "square",
            22.497,
            1,
        ),  # main_beam_c
    ],
)
def test_dovetailmortise_params(
    cross_beams,
    cutting_frame,
    test_index,
    expected_mortise_params,
    start_depth,
    angle,
    length,
    width,
    depth,
    cone_angle,
    flank_angle,
    shape,
    shape_radius,
    ref_side_index,
):
    # Create the StepJoint
    dovetail_mortise = DovetailMortise.from_frame_and_beam(
        cutting_frame,
        cross_beams[test_index],
        start_depth,
        angle,
        length,
        width,
        depth,
        cone_angle,
        flank_angle,
        shape,
        shape_radius,
        ref_side_index,
    )

    # Validate generated parameters
    generated_params = dovetail_mortise.params_dict
    for key, value in expected_mortise_params.items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "test_index, expected_tenon_params, expected_frame",
    [
        (0, EXPECTED_TENON_PARAMS[0], TENON_CUTTING_FRAMES[0]),
        (1, EXPECTED_TENON_PARAMS[1], TENON_CUTTING_FRAMES[1]),
        (2, EXPECTED_TENON_PARAMS[2], TENON_CUTTING_FRAMES[2]),
    ],
)
def test_dovetailtenon_frame_from_params(
    main_beams,
    test_index,
    expected_tenon_params,
    expected_frame,
):
    # convert string values to the appropriate types (float, bool, etc.)
    def convert_value(value):
        if isinstance(value, str):
            # convert to float if the string represents a number
            if value.replace(".", "", 1).isdigit():
                return float(value)
            # convert specific strings to booleans
            if value.lower() in ["yes", "no"]:
                return value.lower() == "yes"
        return value

    # convert the OrderedDict values to the expected types
    params = {key.lower(): convert_value(value) for key, value in expected_tenon_params.items()}

    # instantiate DovetailTenon with unpacked parameters from the OrderedDict
    dovetail_tenon = DovetailTenon(
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
        cone_angle=params["coneangle"],
        use_flank_angle=params["useflankangle"],
        flank_angle=params["flankangle"],
        shape=params["shape"],
        shape_radius=params["shaperadius"],
        ref_side_index=int(params["referenceplaneid"] - 1),
    )

    # generate frame from the parameters
    generated_frame = dovetail_tenon.frame_from_params_and_beam(main_beams[test_index])
    assert generated_frame == expected_frame

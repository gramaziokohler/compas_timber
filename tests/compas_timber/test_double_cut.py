import pytest

from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Line
from compas.geometry import Vector

from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber._fabrication import DoubleCut


@pytest.fixture
def cross_beam():
    width = 100
    height = 120

    centerline = Line(Point(x=33782.4296640, y=-3257.66821289, z=0.0), Point(x=30782.4296640, y=-3257.66821289, z=0.0))

    return Beam.from_centerline(centerline, width, height)


@pytest.fixture
def main_beams():
    width = 80
    height = 100
    normal = Vector(1, 1.5, 0)

    centerlines = [
        Line(
            Point(x=30499.6181909, y=-4472.85889623, z=-1495.56306376), Point(x=31205.1038160, y=-3257.66821289, z=0.0)
        ),
        Line(
            Point(x=32075.5938981, y=-4033.05172213, z=175.130197043), Point(x=31955.6464870, y=-3257.66821289, z=0.0)
        ),
        Line(
            Point(x=32525.3966898, y=-1527.48357877, z=-1380.20828658), Point(x=32425.4405138, y=-3257.66821289, z=0.0)
        ),
        Line(
            Point(x=34264.6341510, y=-3873.12184064, z=752.091392287), Point(x=33288.3954994, y=-3257.66821289, z=0.0)
        ),
    ]

    return [Beam.from_centerline(centerline, width, height, normal) for centerline in centerlines]


EXPECTED_DOUBLE_CUT_PARAMS = [
    OrderedDict(
        [
            ("Name", "DoubleCut"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "end"),
            ("StartX", "1985.301"),
            ("StartY", "30.003"),
            ("Angle1", "46.889"),
            ("Inclination1", "93.332"),
            ("Angle2", "134.670"),
            ("Inclination2", "56.374"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DoubleCut"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "end"),
            ("StartX", "737.894"),
            ("StartY", "16.182"),
            ("Angle1", "43.966"),
            ("Inclination1", "18.288"),
            ("Angle2", "101.632"),
            ("Inclination2", "100.024"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DoubleCut"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "end"),
            ("StartX", "2137.082"),
            ("StartY", "31.908"),
            ("Angle1", "62.107"),
            ("Inclination1", "117.921"),
            ("Angle2", "132.439"),
            ("Inclination2", "57.581"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "DoubleCut"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("Orientation", "end"),
            ("StartX", "1205.229"),
            ("StartY", "96.426"),
            ("Angle1", "27.958"),
            ("Inclination1", "72.366"),
            ("Angle2", "88.776"),
            ("Inclination2", "146.899"),
        ]
    ),
]


EXPECTED_CUTTING_PLANES = [
    [
        Plane(
            point=Point(x=31224.1239747, y=-3307.66821289, z=-59.9999999995),
            normal=Vector(x=-1.01893407715e-16, y=6.79289384764e-17, z=-1.0),
        ),
        Plane(
            point=Point(x=31224.1239747, y=-3307.66821289, z=-59.9999999995),
            normal=Vector(x=5.24602991441e-15, y=-1.0, z=6.24198463444e-16),
        ),
    ],
    [
        Plane(
            point=Point(x=31987.3059470, y=-3307.66821289, z=59.9999999999),
            normal=Vector(x=-9.2376139442e-17, y=6.15840929613e-17, z=1.0),
        ),
        Plane(
            point=Point(x=31987.3059470, y=-3307.66821289, z=59.9999999999),
            normal=Vector(x=-1.38695476766e-16, y=-1.0, z=5.90388154506e-17),
        ),
    ],
    [
        Plane(
            point=Point(x=32469.9263052, y=-3207.66821289, z=-60.0000000004),
            normal=Vector(x=-1.02714686652e-16, y=1.0, z=1.71874245103e-16),
        ),
        Plane(
            point=Point(x=32469.9263052, y=-3207.66821289, z=-60.0000000004),
            normal=Vector(x=1.63477500676e-16, y=2.44472009656e-17, z=-1.0),
        ),
    ],
    [
        Plane(
            point=Point(x=33453.7063922, y=-3307.66821289, z=60.0000000000),
            normal=Vector(x=-3.02234139005e-16, y=-1.0, z=-1.41357928117e-16),
        ),
        Plane(
            point=Point(x=33453.7063922, y=-3307.66821289, z=60.0000000000),
            normal=Vector(x=-6.92821045815e-17, y=2.46336371845e-16, z=1.0),
        ),
    ],
]


@pytest.mark.parametrize(
    "test_index, expected_double_cut_params, cutting_plane_indexes, ref_side_index",
    [
        (0, EXPECTED_DOUBLE_CUT_PARAMS[0], [0, 1], 1),  # main_beam_a
        (1, EXPECTED_DOUBLE_CUT_PARAMS[1], [1, 2], 1),  # main_beam_b
        (2, EXPECTED_DOUBLE_CUT_PARAMS[2], [3, 0], 1),  # main_beam_c
        (3, EXPECTED_DOUBLE_CUT_PARAMS[3], [2, 1], 3),  # main_beam_d
    ],
)
def test_double_cut_params(
    main_beams,
    cross_beam,
    test_index,
    expected_double_cut_params,
    cutting_plane_indexes,
    ref_side_index,
):
    # Create the DoubleCut object
    cutting_planes = [cross_beam.ref_sides[index] for index in cutting_plane_indexes]
    double_cut = DoubleCut.from_planes_and_beam(cutting_planes, main_beams[test_index], ref_side_index)

    # Validate generated parameters
    generated_params = double_cut.params_dict
    for key, value in expected_double_cut_params.items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "test_index, expected_double_cut_params, expected_cutting_planes",
    [
        (0, EXPECTED_DOUBLE_CUT_PARAMS[0], EXPECTED_CUTTING_PLANES[0]),
        (1, EXPECTED_DOUBLE_CUT_PARAMS[1], EXPECTED_CUTTING_PLANES[1]),
        (2, EXPECTED_DOUBLE_CUT_PARAMS[2], EXPECTED_CUTTING_PLANES[2]),
        (3, EXPECTED_DOUBLE_CUT_PARAMS[3], EXPECTED_CUTTING_PLANES[3]),
    ],
)
def test_double_cut_planes_from_params(
    main_beams,
    test_index,
    expected_double_cut_params,
    expected_cutting_planes,
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
    params = {key.lower(): convert_value(value) for key, value in expected_double_cut_params.items()}

    # instantiate DoubleCut with unpacked parameters from the OrderedDict
    double_cut = DoubleCut(
        orientation=params["orientation"],
        start_x=params["startx"],
        start_y=params["starty"],
        angle_1=params["angle1"],
        inclination_1=params["inclination1"],
        angle_2=params["angle2"],
        inclination_2=params["inclination2"],
        ref_side_index=int(params["referenceplaneid"] - 1),
    )

    # generate frame from the parameters
    generated_planes = double_cut.planes_from_params_and_beam(main_beams[test_index])
    # compare generated planes to expected planes using `approx`
    for generated, expected in zip(generated_planes, expected_cutting_planes):
        assert generated.point.x == pytest.approx(expected.point.x, abs=TOL.approximation)
        assert generated.point.y == pytest.approx(expected.point.y, abs=TOL.approximation)
        assert generated.point.z == pytest.approx(expected.point.z, abs=TOL.approximation)
        assert generated.normal.x == pytest.approx(expected.normal.x, abs=TOL.approximation)
        assert generated.normal.y == pytest.approx(expected.normal.y, abs=TOL.approximation)
        assert generated.normal.z == pytest.approx(expected.normal.z, abs=TOL.approximation)

import pytest

from collections import OrderedDict

from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Vector

from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.fabrication import Lap


@pytest.fixture
def cross_beam():
    width = 100
    height = 120

    centerline = Line(
        Point(x=30396.1444398, y=-3257.66821289, z=73.5839565671),
        Point(x=34824.6096086, y=-3257.66821289, z=73.5839565671),
    )

    return Beam.from_centerline(centerline, width, height)


@pytest.fixture
def main_beams():
    width = 80
    height = 100

    centerlines = [
        Line(
            Point(x=32079.4104241, y=-3257.66821289, z=73.5839565671),
            Point(x=33474.4091319, y=-4826.83669239, z=1616.81118820),
        ),
        Line(Point(x=33636.4572343, y=-2124.34355562, z=0.0), Point(x=32465.6288321, y=-3257.66821289, z=73.5839565671)),
        Line(
            Point(x=34148.4484099, y=-3257.66821289, z=1333.76053347),
            Point(x=33438.9952150, y=-3257.66821289, z=73.5839565671),
        ),
        Line(
            Point(x=34328.9231602, y=-3257.66821289, z=73.5839565671),
            Point(x=35365.5736795, y=-2579.64848379, z=-2050.47736312),
        ),
    ]

    return [Beam.from_centerline(centerline, width, height) for centerline in centerlines]


EXPECTED_LAP_PARAMS = [
    OrderedDict(
        [
            ("Name", "Lap"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("Orientation", "start"),
            ("StartX", "1665.305"),
            ("StartY", "0.000"),
            ("Angle", "90.000"),
            ("Inclination", "90.000"),
            ("Slope", "0.000"),
            ("Length", "115.933"),
            ("Width", "120.000"),
            ("Depth", "10.000"),
            ("LeadAngleParallel", "yes"),
            ("LeadAngle", "90.000"),
            ("LeadInclinationParallel", "yes"),
            ("LeadInclination", "90.000"),
            (
                "MachiningLimits",
                OrderedDict(
                    [
                        ("FaceLimitedBack", "no"),
                        ("FaceLimitedEnd", "yes"),
                        ("FaceLimitedFront", "no"),
                        ("FaceLimitedStart", "yes"),
                    ]
                ),
            ),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Lap"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "start"),
            ("StartX", "2053.296"),
            ("StartY", "0.000"),
            ("Angle", "90.000"),
            ("Inclination", "90.000"),
            ("Slope", "0.000"),
            ("Length", "125.355"),
            ("Width", "120.000"),
            ("Depth", "10.000"),
            ("LeadAngleParallel", "yes"),
            ("LeadAngle", "90.000"),
            ("LeadInclinationParallel", "yes"),
            ("LeadInclination", "90.000"),
            (
                "MachiningLimits",
                OrderedDict(
                    [
                        ("FaceLimitedBack", "no"),
                        ("FaceLimitedEnd", "yes"),
                        ("FaceLimitedFront", "no"),
                        ("FaceLimitedStart", "yes"),
                    ]
                ),
            ),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Lap"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("Orientation", "start"),
            ("StartX", "3013.621"),
            ("StartY", "0.000"),
            ("Angle", "90.000"),
            ("Inclination", "90.000"),
            ("Slope", "0.000"),
            ("Length", "120.388"),
            ("Width", "100.000"),
            ("Depth", "10.000"),
            ("LeadAngleParallel", "yes"),
            ("LeadAngle", "90.000"),
            ("LeadInclinationParallel", "yes"),
            ("LeadInclination", "90.000"),
            (
                "MachiningLimits",
                OrderedDict(
                    [
                        ("FaceLimitedBack", "no"),
                        ("FaceLimitedEnd", "yes"),
                        ("FaceLimitedFront", "no"),
                        ("FaceLimitedStart", "yes"),
                    ]
                ),
            ),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Lap"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "1"),
            ("Orientation", "start"),
            ("StartX", "3865.756"),
            ("StartY", "0.000"),
            ("Angle", "123.187"),
            ("Inclination", "90.000"),
            ("Slope", "0.000"),
            ("Length", "121.594"),
            ("Width", "100.000"),
            ("Depth", "10.000"),
            ("LeadAngleParallel", "yes"),
            ("LeadAngle", "90.000"),
            ("LeadInclinationParallel", "yes"),
            ("LeadInclination", "90.000"),
            (
                "MachiningLimits",
                OrderedDict(
                    [
                        ("FaceLimitedBack", "no"),
                        ("FaceLimitedEnd", "yes"),
                        ("FaceLimitedFront", "no"),
                        ("FaceLimitedStart", "yes"),
                    ]
                ),
            ),
        ]
    ),
]

EXPECTED_CUTTING_FRAMES = [
    Frame(
        point=Point(x=32089.6304179, y=-3208.96062535, z=113.871952827),
        xaxis=Vector(x=0.535356833682, y=-0.602197739702, z=0.59224230086),
        yaxis=Vector(x=0.393493090239, y=-0.442621882493, z=-0.805759925209),
    ),
    Frame(
        point=Point(x=33665.8981258, y=-2151.51562805, z=49.9490979824),
        xaxis=Vector(x=-0.717789410535, y=-0.6947973214, z=0.0451114652743),
        yaxis=Vector(x=-0.0324135303495, y=-0.0313752665244, z=-0.998981959647),
    ),
    Frame(
        point=Point(x=34104.8785573, y=-3217.66821289, z=1358.28945402),
        xaxis=Vector(x=-0.490578411027, y=0.0, z=-0.871397052229),
        yaxis=Vector(x=-0.0, y=-1.0, z=0.0),
    ),
    Frame(
        point=Point(x=34270.8814019, y=-3247.83444818, z=48.3956383955),
        xaxis=Vector(x=0.421598058227, y=0.275745582418, z=-0.863839945288),
        yaxis=Vector(x=0.547367991266, y=-0.836892037325, z=-2.77555756156e-17),
    ),
]

EXPECTED_BOX = [
    Box(
        xsize=115.932621049,
        ysize=1200.0,
        zsize=10.0,
        frame=Frame(
            point=Point(x=32119.4156515, y=-3302.66821289, z=73.5839565671),
            xaxis=Vector(x=1.0, y=-2.05374699157e-16, z=0.0),
            yaxis=Vector(x=1.25751580751e-32, y=6.12303176911e-17, z=-1.0),
        ),
    ),
    Box(
        xsize=125.355190923,
        ysize=1200.0,
        zsize=10.0,
        frame=Frame(
            point=Point(x=32512.1179628, y=-3212.66821289, z=73.5839565671),
            xaxis=Vector(x=1.0, y=-2.05374699157e-16, z=0.0),
            yaxis=Vector(x=1.25751580751e-32, y=6.12303176911e-17, z=1.0),
        ),
    ),
    Box(
        xsize=120.388041068,
        ysize=1000.0,
        zsize=10.0,
        frame=Frame(
            point=Point(x=33469.9590708, y=-3257.66821289, z=128.583956567),
            xaxis=Vector(x=1.0, y=4.26515051461e-17, z=0.0),
            yaxis=Vector(x=4.26515051461e-17, y=-1.0, z=1.22460635382e-16),
        ),
    ),
    Box(
        xsize=121.593895035,
        ysize=1000.0,
        zsize=10.0,
        frame=Frame(
            point=Point(x=34340.1491250, y=-3216.23451172, z=18.5839565671),
            xaxis=Vector(x=0.836892037325, y=0.547367991266, z=0.0),
            yaxis=Vector(x=-0.547367991266, y=0.836892037325, z=0.0),
        ),
    ),
]


@pytest.mark.parametrize(
    "expected_lap_params, expected_cutting_frames, width, depth, ref_side_index",
    [
        (EXPECTED_LAP_PARAMS[0], EXPECTED_CUTTING_FRAMES[0], 80, 10, 3),  # main_beam_a
        (EXPECTED_LAP_PARAMS[1], EXPECTED_CUTTING_FRAMES[1], 80, 10, 1),  # main_beam_b
        (EXPECTED_LAP_PARAMS[2], EXPECTED_CUTTING_FRAMES[2], 100, 10, 2),  # main_beam_c
        (EXPECTED_LAP_PARAMS[3], EXPECTED_CUTTING_FRAMES[3], 100, 10, 0),  # main_beam_d
    ],
)
def test_lap_params(
    cross_beam,
    expected_lap_params,
    expected_cutting_frames,
    width,
    depth,
    ref_side_index,
):
    # Create the Lap object
    lap = Lap.from_plane_and_beam(expected_cutting_frames, cross_beam, width, depth, ref_side_index)

    # Validate generated parameters
    generated_params = lap.params_dict
    for key, value in expected_lap_params.items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "expected_lap_params, expected_box",
    [
        (EXPECTED_LAP_PARAMS[0], EXPECTED_BOX[0]),
        (EXPECTED_LAP_PARAMS[1], EXPECTED_BOX[1]),
        (EXPECTED_LAP_PARAMS[2], EXPECTED_BOX[2]),
        (EXPECTED_LAP_PARAMS[3], EXPECTED_BOX[3]),
    ],
)
def test_lap_box_from_params(
    cross_beam,
    expected_lap_params,
    expected_box,
):
    # convert string values to the appropriate types (float, bool, etc.)
    def convert_ordered_dict(params):
        def convert_value(value):
            if isinstance(value, str):
                # Convert to float if the string represents a number
                try:
                    return float(value)
                except ValueError:
                    pass
                # Convert specific strings to booleans
                if value.lower() == "yes":
                    return True
                elif value.lower() == "no":
                    return False
            # If the value is an OrderedDict, recursively convert its items
            elif isinstance(value, OrderedDict):
                return OrderedDict((key, convert_value(val)) for key, val in value.items())
            return value

        # Retain the original casing of keys in the OrderedDict
        return OrderedDict((key, convert_value(value)) for key, value in params.items())

    # convert the OrderedDict values to the expected types
    params = convert_ordered_dict(expected_lap_params)

    # instantiate Lap with unpacked parameters from the OrderedDict
    lap = Lap(
        orientation=params["Orientation"],
        start_x=params["StartX"],
        start_y=params["StartY"],
        angle=params["Angle"],
        inclination=params["Inclination"],
        slope=params["Slope"],
        length=params["Length"],
        width=params["Width"],
        depth=params["Depth"],
        lead_angle_parallel=params["LeadAngleParallel"],
        lead_angle=params["LeadAngle"],
        lead_inclination_parallel=params["LeadInclinationParallel"],
        lead_inclination=params["LeadInclination"],
        machining_limits=params["MachiningLimits"],
        ref_side_index=int(params["ReferencePlaneID"] - 1),
    )

    # generate frame from the parameters
    generated_box = lap.volume_from_params_and_beam(cross_beam)
    print(generated_box)

    # set the tolerance for comparing the generated and expected boxes
    tolerance = Tolerance()
    tolerance.absolute = 1e-3

    def approx_point(p1, p2, tolerance):
        return tolerance.is_close(p1.x, p2.x) and tolerance.is_close(p1.y, p2.y) and tolerance.is_close(p1.z, p2.z)

    # compare generated planes to expected planes using `approx`
    assert tolerance.is_close(generated_box.xsize, expected_box.xsize)
    assert tolerance.is_close(generated_box.ysize, expected_box.ysize)
    assert tolerance.is_close(generated_box.zsize, expected_box.zsize)
    assert approx_point(generated_box.frame.point, expected_box.frame.point, tolerance)
    assert approx_point(generated_box.frame.xaxis, expected_box.frame.xaxis, tolerance)
    assert approx_point(generated_box.frame.yaxis, expected_box.frame.yaxis, tolerance)
    assert approx_point(generated_box.frame.zaxis, expected_box.frame.zaxis, tolerance)

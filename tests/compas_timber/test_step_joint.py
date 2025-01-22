import pytest

from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Line

from compas_timber.elements import Beam
from compas_timber.fabrication import StepJointNotch
from compas_timber.fabrication import StepJoint


@pytest.fixture
def cross_beam():
    width = 80
    height = 120

    centerline = Line(
        Point(x=30782.4296640, y=-3257.66821289, z=73.5839565671),
        Point(x=33782.4296640, y=-3257.66821289, z=73.5839565671),
    )

    return Beam.from_centerline(centerline, width, height)


@pytest.fixture
def main_beams():
    width = 60
    height = 80

    centerlines = [
        Line(
            Point(x=31332.0787451, y=-3257.66821289, z=73.5839565671),
            Point(x=32047.6038329, y=-3257.66821289, z=1075.65737239),
        ),
        Line(
            Point(x=32112.1101310, y=-3257.66821289, z=73.5839565671),
            Point(x=31866.4722928, y=-4147.31599571, z=73.5839565671),
        ),
        Line(
            Point(x=33434.6730831, y=-2332.78139486, z=73.5839565671),
            Point(x=32910.9934277, y=-3257.66821289, z=73.5839565671),
        ),
    ]

    return [Beam.from_centerline(centerline, width, height) for centerline in centerlines]


EXPECTED_NOTCH_PARAMS = [
    OrderedDict(
        [
            ("Name", "StepJointNotch"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("Orientation", "end"),
            ("StartX", "641.642"),
            ("StartY", "10.000"),
            ("StrutInclination", "125.529"),
            ("NotchLimited", "yes"),
            ("NotchWidth", "60.000"),
            ("StepDepth", "20.000"),
            ("HeelDepth", "0.000"),
            ("StrutHeight", "80.000"),
            ("StepShape", "step"),
            ("Mortise", "no"),
            ("MortiseWidth", "40.000"),
            ("MortiseHeight", "40.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "StepJointNotch"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("Orientation", "start"),
            ("StartX", "1287.514"),
            ("StartY", "0.000"),
            ("StrutInclination", "105.435"),
            ("NotchLimited", "no"),
            ("NotchWidth", "80.000"),
            ("StepDepth", "0.000"),
            ("HeelDepth", "10.000"),
            ("StrutHeight", "60.000"),
            ("StepShape", "heel"),
            ("Mortise", "no"),
            ("MortiseWidth", "40.000"),
            ("MortiseHeight", "40.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "StepJointNotch"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "end"),
            ("StartX", "2185.687"),
            ("StartY", "0.000"),
            ("StrutInclination", "119.519"),
            ("NotchLimited", "no"),
            ("NotchWidth", "80.000"),
            ("StepDepth", "20.000"),
            ("HeelDepth", "10.000"),
            ("StrutHeight", "60.000"),
            ("StepShape", "double"),
            ("Mortise", "no"),
            ("MortiseWidth", "40.000"),
            ("MortiseHeight", "40.000"),
        ]
    ),
]

EXPECTED_STEP_PARAMS = [
    OrderedDict(
        [
            ("Name", "StepJoint"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "1"),
            ("Orientation", "start"),
            ("StartX", "102.288"),
            ("StrutInclination", "125.529"),
            ("StepDepth", "20.000"),
            ("HeelDepth", "0.000"),
            ("StepShape", "step"),
            ("Tenon", "no"),
            ("TenonWidth", "40.000"),
            ("TenonHeight", "40.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "StepJoint"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("Orientation", "start"),
            ("StartX", "49.780"),
            ("StrutInclination", "105.435"),
            ("StepDepth", "0.000"),
            ("HeelDepth", "10.000"),
            ("StepShape", "heel"),
            ("Tenon", "no"),
            ("TenonWidth", "40.000"),
            ("TenonHeight", "40.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "StepJoint"),
            ("Priority", "0"),
            ("Process", "yes"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("Orientation", "end"),
            ("StartX", "999.900"),
            ("StrutInclination", "119.519"),
            ("StepDepth", "20.000"),
            ("HeelDepth", "10.000"),
            ("StepShape", "double"),
            ("Tenon", "no"),
            ("TenonWidth", "40.000"),
            ("TenonHeight", "40.000"),
        ]
    ),
]


@pytest.mark.parametrize(
    "main_beam_index, expected_notch_params, cutting_plane_index, start_y, notch_limited, notch_width, step_depth, heel_depth, strut_height, tapered_heel, ref_side_index",
    [
        (0, EXPECTED_NOTCH_PARAMS[0], 0, 10.0, True, 60.0, 20.0, 0.0, 80.0, False, 2),  # main_beam_a
        (1, EXPECTED_NOTCH_PARAMS[1], 3, 0.0, False, 80.0, 0.0, 10.0, 60.0, False, 3),  # main_beam_b
        (2, EXPECTED_NOTCH_PARAMS[2], 1, 0.0, False, 80.0, 20.0, 10.0, 60.0, False, 1),  # main_beam_c
    ],
)
def test_stepjointnotch_params(
    main_beams,
    cross_beam,
    main_beam_index,
    expected_notch_params,
    cutting_plane_index,
    start_y,
    notch_limited,
    notch_width,
    step_depth,
    heel_depth,
    strut_height,
    tapered_heel,
    ref_side_index,
):
    # Create the StepJointNotch
    step_joint_notch = StepJointNotch.from_plane_and_beam(
        plane=main_beams[main_beam_index].ref_sides[cutting_plane_index],
        beam=cross_beam,
        start_y=start_y,
        notch_limited=notch_limited,
        notch_width=notch_width,
        step_depth=step_depth,
        heel_depth=heel_depth,
        strut_height=strut_height,
        tapered_heel=tapered_heel,
        ref_side_index=ref_side_index,
    )

    # Validate generated parameters
    generated_params = step_joint_notch.params_dict
    for key, value in expected_notch_params.items():
        assert generated_params[key] == value


@pytest.mark.parametrize(
    "main_beam_index, expected_step_params, cutting_plane_index, step_depth, heel_depth, tapered_heel, ref_side_index",
    [
        (0, EXPECTED_STEP_PARAMS[0], 2, 20.0, 0.0, False, 0),  # main_beam_a
        (1, EXPECTED_STEP_PARAMS[1], 3, 0.0, 10.0, False, 3),  # main_beam_b
        (2, EXPECTED_STEP_PARAMS[2], 1, 20.0, 10.0, False, 1),  # main_beam_c
    ],
)
def test_stepjoint_params(
    main_beams,
    cross_beam,
    main_beam_index,
    expected_step_params,
    cutting_plane_index,
    step_depth,
    heel_depth,
    tapered_heel,
    ref_side_index,
):
    # Create the StepJoint
    step_joint = StepJoint.from_plane_and_beam(
        cross_beam.ref_sides[cutting_plane_index],
        main_beams[main_beam_index],
        step_depth,
        heel_depth,
        tapered_heel,
        ref_side_index,
    )

    # Validate generated parameters
    generated_params = step_joint.params_dict
    for key, value in expected_step_params.items():
        assert generated_params[key] == value

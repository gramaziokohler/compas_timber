import pytest

from collections import OrderedDict

from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import Point
from compas.geometry import Line

from compas_timber.connections import TStepJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import StepJointNotch
from compas_timber.fabrication import StepJoint
from compas_timber.fabrication import StepShapeType
from compas_timber.fabrication import OrientationType
from compas_timber.model import TimberModel


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
    generated_params = step_joint_notch.params.header_attributes
    generated_params.update(step_joint_notch.params.as_dict())
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
    generated_params = step_joint.params.header_attributes
    generated_params.update(step_joint.params.as_dict())
    for key, value in expected_step_params.items():
        assert generated_params[key] == value


def test_stepjoint_scaled():
    step_joint = StepJoint(
        orientation=OrientationType.START,
        start_x=0.0,
        strut_inclination=92.0,
        step_depth=20.0,
        heel_depth=20.0,
        step_shape=StepShapeType.DOUBLE,
        tenon=False,
        tenon_width=40.0,
        tenon_height=40.0,
        ref_side_index=1,
    )

    scaled = step_joint.scaled(2.0)

    assert scaled.orientation == step_joint.orientation
    assert scaled.start_x == step_joint.start_x * 2.0
    assert scaled.strut_inclination == step_joint.strut_inclination
    assert scaled.step_depth == step_joint.step_depth * 2.0
    assert scaled.heel_depth == step_joint.heel_depth * 2.0
    assert scaled.step_shape == step_joint.step_shape
    assert scaled.tenon == step_joint.tenon
    assert scaled.tenon_width == step_joint.tenon_width * 2.0
    assert scaled.tenon_height == step_joint.tenon_height * 2.0
    assert scaled.ref_side_index == step_joint.ref_side_index


def test_tstepjoint_creates_expected_processings():
    """Test that TStepJoint correctly calculates dimensions for different reference side orientations."""
    expected_notch_params = {
        "Orientation": "end",
        "StartX": "1085.678",
        "StartY": "0.000",
        "StrutInclination": "109.993",
        "NotchLimited": "no",
        "NotchWidth": "80.000",
        "StepDepth": "30.000",
        "HeelDepth": "0.000",
        "StrutHeight": "120.000",
        "StepShape": "step",
        "Mortise": "no",
        "MortiseWidth": "40.000",
        "MortiseHeight": "40.000",
    }
    expected_step_params = {
        "Orientation": "start",
        "StartX": "171.355",
        "StrutInclination": "109.993",
        "StepDepth": "30.000",
        "HeelDepth": "0.000",
        "StepShape": "step",
        "Tenon": "no",
        "TenonWidth": "40.000",
        "TenonHeight": "40.000",
    }

    # Create beams with specific frames as provided
    beam_width = 80
    beam_height = 120

    # Cross beam (first beam)
    cross_frame = Frame(point=Point(x=-3000.000, y=7000.000, z=0.000), xaxis=Vector(x=0.000, y=-1.000, z=0.000), yaxis=Vector(x=1.000, y=0.000, z=-0.000))
    cross_beam = Beam(frame=cross_frame, width=beam_width, height=beam_height, length=2000.000)
    cross_beam.attributes["name"] = "cross_beam"

    # Main beam (second beam)
    main_frame = Frame(point=Point(x=-3000.000, y=6000.000, z=0.000), xaxis=Vector(x=0.000, y=-0.342, z=0.940), yaxis=Vector(x=1.000, y=0.000, z=-0.000))
    main_beam = Beam(frame=main_frame, width=beam_width, height=beam_height, length=1000.000)
    main_beam.attributes["name"] = "main_beam"

    # Create TStepJoint
    model = TimberModel()
    model.add_elements([cross_beam, main_beam])
    _ = TStepJoint.create(model, main_beam, cross_beam)

    model.process_joinery()

    # Validate generated parameters with expeccted processing parameters
    for beam in model.beams:
        if isinstance(beam.features[0], StepJointNotch):
            notch = beam.features[0]
            generated_notch_params = notch.params.as_dict()
            for key, value in expected_notch_params.items():
                assert generated_notch_params[key] == value
        if isinstance(beam.features[0], StepJoint):
            step = beam.features[0]
            generated_step_params = step.params.as_dict()
            for key, value in expected_step_params.items():
                assert generated_step_params[key] == value

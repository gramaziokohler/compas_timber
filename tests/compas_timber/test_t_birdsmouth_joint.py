import math

import pytest
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_brep import Brep

from compas_timber.connections import TBirdsmouthJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import Lap
from compas_timber.model import TimberModel


@pytest.fixture
def model_and_beams():
    # main beam tilted 30 degrees upwards, ending at the centerline of the cross beam
    angle = math.radians(30)
    start = Point(0, 800 * math.cos(angle), 800 * math.sin(angle))
    main_beam = Beam.from_centerline(Line(start, Point(0, 0, 0)), width=80, height=160, z_vector=Vector(0, 0, 1))
    cross_beam = Beam.from_centerline(Line(Point(-600, 0, 0), Point(600, 0, 0)), width=80, height=160, z_vector=Vector(0, 0, 1))
    model = TimberModel()
    model.add_element(main_beam)
    model.add_element(cross_beam)
    return model, main_beam, cross_beam


def _expected_lap_params(width):
    return {
        "Orientation": "end",
        "StartX": "640.000",
        "StartY": "0.000",
        "Angle": "90.000",
        "Inclination": "90.000",
        "Slope": "0.000",
        "Length": "80.000",
        "Width": width,
        "Depth": "20.000",
        "LeadAngleParallel": "yes",
        "LeadAngle": "90.000",
        "LeadInclinationParallel": "yes",
        "LeadInclination": "90.000",
        "MachiningLimits": {
            "FaceLimitedStart": "yes",
            "FaceLimitedEnd": "yes",
            "FaceLimitedFront": "no",
            "FaceLimitedBack": "no",
            "FaceLimitedTop": "no",
            "FaceLimitedBottom": "yes",
        },
    }


def test_t_birdsmouth_joint_without_mill_depth_does_not_mill_cross_beam(model_and_beams):
    model, main_beam, cross_beam = model_and_beams
    TBirdsmouthJoint.create(model, main_beam, cross_beam)

    model.process_joinery()

    assert cross_beam.features == []


def test_t_birdsmouth_joint_mill_depth_adds_laps_to_cross_beam(model_and_beams):
    model, main_beam, cross_beam = model_and_beams
    TBirdsmouthJoint.create(model, main_beam, cross_beam, mill_depth=20.0)

    model.process_joinery()

    laps = cross_beam.features
    assert all(isinstance(lap, Lap) for lap in laps)
    # one lap on each of the two sides of the cross beam the main beam sits on
    assert [lap.ref_side_index for lap in laps] == [1, 2]
    assert [lap.params.as_dict() for lap in laps] == [_expected_lap_params("160.000"), _expected_lap_params("80.000")]


@pytest.mark.requires_occ
def test_t_birdsmouth_joint_mill_depth_geometry(model_and_beams):
    model, main_beam, cross_beam = model_and_beams
    TBirdsmouthJoint.create(model, main_beam, cross_beam, mill_depth=20.0)

    model.process_joinery()

    main_geometry = main_beam.geometry
    cross_geometry = cross_beam.geometry
    assert not main_beam.debug_info
    assert not cross_beam.debug_info
    # pockets of 80 x 160 x 20 and 80 x 80 x 20 in the two sides of the cross beam, which share an 80 x 20 x 20 corner
    cross_blank = Brep.from_box(cross_beam.blank)
    pocket_volume = 80 * 160 * 20 + 80 * 80 * 20 - 80 * 20 * 20
    assert TOL.is_close(cross_blank.volume - cross_geometry.volume, pocket_volume)
    # the main beam reaches into the pockets without overlapping the cross beam
    assert not Brep.from_boolean_intersection(main_geometry, cross_geometry)
    assert Brep.from_boolean_intersection(main_geometry, cross_blank)

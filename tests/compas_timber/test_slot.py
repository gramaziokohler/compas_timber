import pytest
from collections import OrderedDict

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Vector

from compas_timber.elements import Beam
from compas_timber.fabrication import Slot


@pytest.fixture
def beam():
    width = 60.0
    height = 120.0
    centerline = Line(Point(x=80.4429082858, y=26.8976400207, z=0.0), Point(x=542.848108719, y=26.8976400207, z=0.0))
    return Beam.from_centerline(centerline, width, height)


def test_horizontal_slot_negative_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=90.7489233758, z=55.0906953863),
        xaxis=Vector(x=-0.0214020667979, y=-0.833730649845, z=-0.551756427281),
        yaxis=Vector(x=-0.999699702481, y=0.0244348873403, z=0.00185503105829),
    )
    # TODO: add test for integer values. shouldn't be an issue but it is
    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "0.000"),
            ("StartY", "91.882"),
            ("StartDepth", "0.000"),
            ("Angle", "-33.482"),
            ("Inclination", "88.760"),
            ("Length", "71.937"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            ("MachiningLimits", {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)
    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_horizontal_slot_positive_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=-46.3620774824, z=59.0575029514),
        xaxis=Vector(x=-0.0214020667979, y=0.785041613815, z=-0.619073191243),
        yaxis=Vector(x=-0.999699702481, y=-0.00941182448018, z=0.0226257026303),
    )

    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "0.000"),
            ("StartY", "38.455"),
            ("StartDepth", "0.000"),
            ("Angle", "38.273"),
            ("Inclination", "88.896"),
            ("Length", "76.427"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            ("MachiningLimits", {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)

    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_vertical_slot_positive_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=7.41234277630, z=91.0737369193),
        xaxis=Vector(x=-0.0214020667979, y=0.145153961857, z=-0.989177577028),
        yaxis=Vector(x=-0.999699702481, y=0.00870466402682, z=0.0229070662403),
    )

    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "26.666"),
            ("StartY", "0.000"),
            ("StartDepth", "0.000"),
            ("Angle", "81.667"),
            ("Inclination", "89.309"),
            ("Length", "121.281"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            ("MachiningLimits", {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)

    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values


def test_vertical_slot_negative_angle(beam):
    slot_frame = Frame(
        point=Point(x=137.660612947, y=35.2371162149, z=90.8851505187),
        xaxis=Vector(x=-0.0214020667979, y=-0.183445400082, z=-0.982796894951),
        yaxis=Vector(x=-0.999699702481, y=0.0156622878516, z=0.0188466866799),
    )

    slot_depth = 100.0
    slot_thickness = 10.0
    expected_values = OrderedDict(
        [
            ("Name", "Slot"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("Orientation", "start"),
            ("StartX", "26.739"),
            ("StartY", "120.000"),
            ("StartDepth", "0.000"),
            ("Angle", "-79.412"),
            ("Inclination", "89.304"),
            ("Length", "122.078"),
            ("Depth", "100.000"),
            ("Thickness", "10.000"),
            ("AngleRefPoint", "90.000"),
            ("AngleOppPoint", "90.000"),
            ("AddAngleOppPoint", "0.000"),
            ("MachiningLimits", {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}),
        ]
    )

    slot = Slot.from_plane_and_beam(slot_frame, beam, slot_depth, slot_thickness)

    params = slot.params.header_attributes
    params.update(slot.params.as_dict())
    assert params == expected_values

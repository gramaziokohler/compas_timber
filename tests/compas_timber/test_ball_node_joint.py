import pytest

from compas.geometry import Line
from compas.geometry import Point

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import BallNodeJoint
from compas_timber.fasteners import BallNodeFastener


@pytest.fixture
def beams():
    line1 = Line(Point(0, 0, 0), Point(10, 10, 10))
    line2 = Line(Point(0, 0, 0), Point(10, 0, 10))
    line3 = Line(Point(0, 0, 0), Point(-10, 10, -10))
    line4 = Line(Point(0, 0, 0), Point(-10, 10, -10))
    lines = [line1, line2, line3, line4]
    beams = [Beam.from_centerline(line, width=5, height=15) for line in lines]
    return beams


def test_ball_node_joint(beams):
    model = TimberModel()
    model.add_elements(beams)

    joint = BallNodeJoint.create(model, *beams)

    model.process_joinery()

    assert isinstance(joint, BallNodeJoint)
    assert len(list(model.joints)) == 1
    assert isinstance(list(model.joints)[0], BallNodeJoint)
    assert len(joint.fasteners) == 1
    assert isinstance(joint.fasteners[0], BallNodeFastener)
    assert joint.fasteners[0].ball_diameter == 10
    assert joint.fasteners[0].rods[0].length == 30
    assert len(joint.fasteners[0].rods) == 4

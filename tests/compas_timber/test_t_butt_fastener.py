import pytest

from compas.geometry import Frame, Polyline, Point

from compas_timber.elements import Beam
from compas_timber.fasteners import PlateFastener
from compas_timber.fasteners import PlateFastenerHole
from compas_timber.fasteners import Dowel
from compas_timber.connections import TButtJointPlateFastener
from compas_timber.model import TimberModel


@pytest.fixture
def cross_beam():
    return Beam(Frame([0, 0, 0], [1.000, 0.000, 0.000], [0.000, 1.000, 0.000]), 50.000, 50.000, 745.289)


@pytest.fixture
def main_beam():
    return Beam(Frame([0.5, 0, 0], [-0.707, 0.000, 0.707], [0.000, -1.000, 0.000]), 30, 50.000, 198)


@pytest.fixture
def plate_fastener():
    outline = Polyline([[-0.5, -0.5, 0], [0.5, -0.5, 0], [0.5, 0.5, 0], [-0.5, 0.5, 0], [-0.5, -0.5, 0]])
    plate_fastener = PlateFastener(frame=Frame.worldXY(), outline=outline, thickness=5)
    return plate_fastener


def test_joint_with_fastener(cross_beam, main_beam, plate_fastener):
    model = TimberModel()

    model.add_element(cross_beam)
    model.add_element(main_beam)

    joint = TButtJointPlateFastener.create(
        model,
        main_beam,
        cross_beam,
        mill_depth=30,
        force_pocket=True,
        conical_tool=True,
        base_fastener=plate_fastener,
    )
    assert len(joint.compute_fastener_target_frames()) == 2
    assert len(joint.fasteners) == 2

    model.process_joinery()


def test_joint_with_sub_fastener(cross_beam, main_beam, plate_fastener):
    model = TimberModel()

    model.add_element(cross_beam)
    model.add_element(main_beam)

    hole = PlateFastenerHole(point=Point(0, 0, 0), diameter=2, depth=10)
    plate_fastener.add_hole(hole)
    dowel = Dowel(frame=Frame.worldXY(), height=30, diameter=2, head_bias=5, processings=True)
    plate_fastener.add_sub_fastener(dowel)

    joint = TButtJointPlateFastener.create(
        model,
        main_beam,
        cross_beam,
        mill_depth=30,
        force_pocket=True,
        conical_tool=True,
        base_fastener=plate_fastener,
    )
    assert len(joint.compute_fastener_target_frames()) == 2
    assert len(joint.fasteners) == 4
    assert len(plate_fastener.find_all_nested_sub_fasteners()) == 2

    model.process_joinery()

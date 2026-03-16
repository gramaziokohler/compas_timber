from compas_timber.fabrication.pocket import Polyhedron

import pytest

from compas.geometry import Polyline
from compas.geometry import Frame
from compas.geometry import Point


from compas_timber.fasteners import PlateFastener
from compas_timber.fasteners import PlateFastenerHole


def test_init_fastener():
    outline = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]])
    frame = Frame.worldXY()
    thickness = 4
    fastener = PlateFastener(frame=frame, outline=outline, thickness=thickness)

    assert fastener
    assert fastener.is_fastener
    assert thickness == fastener.thickness
    assert isinstance(fastener.frame, Frame)
    assert isinstance(fastener.outline, Polyline)
    assert isinstance(fastener.target_frame, Frame)
    assert isinstance(fastener.__data__, dict)


def test_plate_hole():
    hole = PlateFastenerHole(point=Point(0.5, 0.5, 0), diameter=0.2, depth=4)
    assert isinstance(hole, PlateFastenerHole)
    assert hole.point == Point(0.5, 0.5, 0)
    assert hole.diameter == 0.2
    assert hole.depth == 4
    assert isinstance(hole.__data__, dict)


@pytest.fixture
def fastener():
    outline = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    frame = Frame.worldXY()
    thickness = 4
    return PlateFastener(frame=frame, outline=outline, thickness=thickness)


@pytest.fixture
def hole():
    return PlateFastenerHole(point=Point(0.3, 0.3, 0), diameter=0.2, depth=4)


def test_hole_in_plate(fastener, hole):
    fastener.add_hole(hole)
    assert len(fastener.holes) == 1
    fastener.add_hole(Point(0.66, 0.66, 0), diameter=0.2, depth=4)
    assert len(fastener.holes) == 2
    assert all(isinstance(hole, PlateFastenerHole) for hole in fastener.holes)


def test_plate_recess(fastener):
    outline = Polyline([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]])
    frame = Frame([0.5, 0.5, 0], [1, 0, 0], [0, 1, 0])
    thickness = 4
    recess = 2
    recess_fastener = PlateFastener(frame=frame, outline=outline, thickness=thickness, recess=recess)
    assert recess_fastener.recess == recess
    assert isinstance(recess_fastener.recess_frame, Frame)
    assert isinstance(recess_fastener.__data__, dict)
    assert recess_fastener.recess_volume
    assert isinstance(recess_fastener.recess_volume, Polyhedron)

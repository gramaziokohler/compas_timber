from compas.geometry import Point
from compas.geometry import Frame
from compas.geometry import Line

from compas_timber.fasteners import RectangularPlate
from compas_timber.fasteners import PlateHole
from compas_timber.fasteners import BallNode
from compas_timber.fasteners import BallNodeRod
from compas_timber.fasteners import BallNodePlate


def test_rectangular_plate():
    plate = RectangularPlate(width=10, height=20, thickness=2)
    assert plate
    assert isinstance(plate, RectangularPlate)
    assert plate.width == 10
    assert plate.height == 20
    assert plate.thickness == 2


def test_rectangular_plate_copy():
    plate = RectangularPlate(width=10, height=20, thickness=2, recess=1, recess_offset=0.5)
    hole = PlateHole(diameter=5, height=2, frame=plate.frame.copy())
    plate.add_hole(hole)
    plate.add_hole_point_diameter(Point(2, 3, 0), diameter=3)

    plate_copy = plate.copy()

    assert plate.width == plate_copy.width
    assert plate.height == plate_copy.height
    assert plate.thickness == plate_copy.thickness
    assert plate.recess == plate_copy.recess
    assert plate.recess_offset == plate_copy.recess_offset
    assert len(plate.holes) == len(plate_copy.holes)
    assert plate.holes[0].diameter == plate_copy.holes[0].diameter
    assert plate.holes[0].height == plate_copy.holes[0].height
    assert plate.holes[0].frame.point == plate_copy.holes[0].frame.point
    assert plate.holes[0].frame.xaxis == plate_copy.holes[0].frame.xaxis
    assert plate.holes[0].frame.yaxis == plate_copy.holes[0].frame.yaxis
    assert plate.holes[1].diameter == plate_copy.holes[1].diameter
    assert plate.holes[1].height == plate_copy.holes[1].height
    assert plate.holes[1].frame.point == plate_copy.holes[1].frame.point
    assert plate.holes[1].frame.xaxis == plate_copy.holes[1].frame.xaxis
    assert plate.holes[1].frame.yaxis == plate_copy.holes[1].frame.yaxis


def test_plate_hole_dirlling_line():
    hole = PlateHole(diameter=5, height=2, frame=Frame.worldXY(), drilling_depth=10, drilling_diameter=3)

    test_line = Line(Point(0, 0, 0), Point(0, 0, -10))

    assert test_line == hole.drilling_line

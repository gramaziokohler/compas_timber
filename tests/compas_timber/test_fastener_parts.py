from compas.geometry import Point
from compas.geometry import Frame
from compas.geometry import Line

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import TButtJoint
from compas_timber.fasteners import RectangularPlate
from compas_timber.fasteners import PlateHole
from compas_timber.fasteners import Fastener


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


def test_rect_plate_features():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)

    model.add_elements([cross_beam, main_beam])

    _ = TButtJoint.create(model, main_beam, cross_beam, mill_depth=3)

    plate = RectangularPlate(width=10, height=5, thickness=2, recess=2, recess_offset=1)
    hole1 = PlateHole(diameter=5, height=2, frame=plate.frame.copy())
    plate.add_hole(hole1)
    fastener = Fastener()
    fastener.add_part(plate)
    fastener.target_frames = [
        Frame(Point(0, -5, 20), [1, 0, 0], [0, 0, 1]),
        Frame(Point(0, 5, 20), [-1, 0, 0], [0, 0, 1]),
    ]

    model.add_fastener(fastener, [main_beam, cross_beam])

    model.process_fasteners()

    assert len(cross_beam.features) == 4
    features_names = [type(f).__name__ for f in cross_beam.features]
    assert features_names.count("Drilling") == 2
    assert features_names.count("Pocket") == 2

    model.process_joinery()
    assert len(cross_beam.features) == 5
    features_names = [type(f).__name__ for f in cross_beam.features]
    assert features_names.count("Drilling") == 2
    assert features_names.count("Pocket") == 2
    assert features_names.count("Lap") == 1

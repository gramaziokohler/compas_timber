from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Transformation

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import PlateHole
from compas_timber.fasteners import RectangularPlate
from compas_timber.model import TimberModel


def test_rectangular_plate():
    plate = RectangularPlate(width=10, height=20, thickness=2)
    assert plate
    assert isinstance(plate, RectangularPlate)
    assert plate.width == 10
    assert plate.height == 20
    assert plate.thickness == 2


def test_rectangular_plate_copy():
    plate = RectangularPlate(width=10, height=20, thickness=2, recess=1, recess_offset=0.5)

    plate_copy = plate.copy()

    assert plate.width == plate_copy.width
    assert plate.height == plate_copy.height
    assert plate.thickness == plate_copy.thickness
    assert plate.recess == plate_copy.recess
    assert plate.recess_offset == plate_copy.recess_offset


def test_rectangular_plate_holes_are_child_parts():
    plate = RectangularPlate(width=10, height=20, thickness=2)
    hole = PlateHole(diameter=5, height=2, frame=Frame.worldXY())
    plate.add_hole(hole)

    assert plate.holes == [hole]
    assert plate.parts == [hole]
    # a hole is a void: it has no geometry of its own, it is cut out of the plate
    assert hole.geometry is None

    fastener = Fastener()
    fastener.add_part(plate)
    assert fastener.all_parts == [plate, hole]
    assert len(fastener.geometry) == 1


def test_rectangular_plate_add_hole_in_model():
    model, main_beam, cross_beam = _straddling_plate_model([])
    plate = model.fasteners[0].parts[0]

    # adding a hole to a plate already in the model puts it straight into the tree
    hole = plate.add_hole_point_diameter(Point(0, -5, 0), diameter=3)

    assert hole.model is model
    assert hole.parent is plate
    assert plate.holes == [hole]


def test_rectangular_plate_holes_model_json_roundtrip():
    model, _, _ = _straddling_plate_model([Point(0, -5, 0), Point(0, 30, 0)])
    plate = model.fasteners[0].parts[0]

    rec_model = json_loads(json_dumps(model))

    rec_plate = rec_model.fasteners[0].parts[0]
    assert len(rec_plate.holes) == 2
    for hole, rec_hole in zip(plate.holes, rec_plate.holes):
        assert isinstance(rec_hole, PlateHole)
        assert rec_hole.parent is rec_plate
        assert rec_hole.diameter == hole.diameter
        assert rec_hole.height == hole.height
        assert rec_hole.placement_frame.point == hole.placement_frame.point

    assert rec_model.process_fasteners() == []
    assert sum(type(f).__name__ == "Drilling" for beam in rec_model.beams for f in beam.features) == 2


def test_rectangular_plate_grid_holes():
    plate = RectangularPlate(width=10, height=20, thickness=2)
    plate.add_holes_grid(3, 5, 2, 2)

    assert len(plate.holes) == 15
    assert all(isinstance(hole, PlateHole) for hole in plate.holes)
    assert all(hole.diameter == 2 for hole in plate.holes)
    assert all(hole.height == 2 for hole in plate.holes)


def test_plate_hole_drilling_line():
    hole = PlateHole(diameter=5, height=2, frame=Frame.worldXY(), drilling_depth=10, drilling_diameter=3)

    test_line = Line(Point(0, 0, 0), Point(0, 0, -10))

    assert test_line == hole.drilling_line


def test_rect_plate_features():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)

    model.add_elements([cross_beam, main_beam])

    _ = TButtJoint.create(model, main_beam, cross_beam, mill_depth=3)

    # two plate parts, one per placement frame (formerly two "target frames")
    fastener = Fastener()
    for frame in [Frame(Point(0, -5, 20), [1, 0, 0], [0, 0, 1]), Frame(Point(0, 5, 20), [-1, 0, 0], [0, 0, 1])]:
        plate = RectangularPlate(width=10, height=5, thickness=2, recess=2, recess_offset=1)
        plate.add_hole(PlateHole(diameter=5, height=2, frame=Frame.worldXY()))
        plate.transformation = Transformation.from_frame(frame)
        plate.elements = [cross_beam]
        fastener.add_part(plate)

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


def _straddling_plate_model(hole_points, drilling_diameter=2):
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])
    TButtJoint.create(model, main_beam, cross_beam, mill_depth=3)

    # a single plate straddling both beams; its local y-axis runs up along the main beam
    fastener = Fastener()
    plate = RectangularPlate(width=10, height=80, thickness=2)
    for point in hole_points:
        plate.add_hole_point_diameter(point, diameter=3, drilling_diameter=drilling_diameter)
    plate.transformation = Transformation.from_frame(Frame(Point(0, -5, 20), [1, 0, 0], [0, 0, 1]))
    plate.elements = [main_beam, cross_beam]
    fastener.add_part(plate)
    model.add_fastener(fastener, [main_beam, cross_beam])
    return model, main_beam, cross_beam


def test_rect_plate_hole_drills_only_the_beam_it_sits_over():
    # one hole over the cross beam (z=15), one over the main beam (z=50)
    model, main_beam, cross_beam = _straddling_plate_model([Point(0, -5, 0), Point(0, 30, 0)])

    errors = model.process_fasteners()

    assert errors == []
    assert [type(f).__name__ for f in cross_beam.features] == ["Drilling"]
    assert [type(f).__name__ for f in main_beam.features] == ["Drilling"]


def test_rect_plate_failed_drilling_is_reported():
    from compas_timber.errors import FastenerApplicationError

    # an invalid drilling diameter must surface as an error instead of silently dropping the drilling
    model, _, _ = _straddling_plate_model([Point(0, -5, 0)], drilling_diameter=-1)

    errors = model.process_fasteners()

    assert len(errors) == 1
    assert isinstance(errors[0], FastenerApplicationError)

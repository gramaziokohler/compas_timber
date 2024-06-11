from compas.data import json_dumps
from compas.data import json_loads
from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Line
from compas.geometry import Vector
from compas.geometry import close

from compas_timber.elements import Beam
from compas_timber.elements import CutFeature
from compas_timber.elements import DrillFeature
from compas_timber.elements import MillVolume


def test_drill_data():
    line = Line([0, 0, 0], [1, 0, 0])
    diameter = 0.2
    length = 0.45

    f = DrillFeature(line, diameter, length, is_joinery=False)
    f = json_loads(json_dumps(f))

    assert isinstance(f, DrillFeature)
    assert f.line == line
    assert f.diameter == diameter
    assert f.length == length
    assert f.is_joinery is False


def test_cut_data():
    plane = Plane(Point(0.4, 0.023, 1.5), Vector(0.02, 0.1, 0.9))
    f = CutFeature(plane, is_joinery=True)
    f = json_loads(json_dumps(f))

    assert isinstance(f, CutFeature)
    assert f.cutting_plane == plane
    assert f.is_joinery is True


def test_mill_volume_data():
    box = Box.from_width_height_depth(1.0, 12.5, 3.0)
    mesh = box.to_mesh()
    f = MillVolume(mesh, is_joinery=False)
    f = json_loads(json_dumps(f))

    assert isinstance(f, MillVolume)
    assert isinstance(f.mesh_volume, Mesh)
    assert f.is_joinery is False


def test_add_extend_start_feature():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)
    beam.add_blank_extension(start=0.10, end=0.0)

    assert close(beam.blank.xsize, 1.1)


def test_add_extend_end_feature():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)

    beam.add_blank_extension(start=0.0, end=0.10)

    assert close(beam.blank.xsize, 1.1)
    # TODO: assert was extended at end and not at start


def test_extend_both_start_end():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)

    beam.add_blank_extension(start=0.10, end=0.10)

    assert close(beam.blank.xsize, 1.2)


def test_accumulate_extension():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)
    beam.add_blank_extension(start=0.0, end=0.10)
    beam.add_blank_extension(start=0.0, end=0.20)

    # max extension is used
    assert close(beam.blank.xsize, 1.20)


def test_remove_parametric_extension():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)
    beam.add_blank_extension(start=0.0, end=0.10)

    assert close(beam.blank.xsize, 1.10)

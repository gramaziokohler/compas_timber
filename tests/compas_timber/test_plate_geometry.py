from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import Frame
from compas.data import json_dumps
from compas.data import json_loads
from compas.tolerance import TOL

from compas_timber.elements import Plate
from compas_timber.elements import PlateGeometry


def test_plate_geometry_serialization():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)
    pg_copy = json_loads(json_dumps(pg))
    assert all([TOL.is_allclose(pg.outline_a.points[i], pg_copy.outline_a.points[i]) for i in range(len(pg.outline_a.points))]), "copied outline_a does not match"



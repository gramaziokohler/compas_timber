from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Plane
from compas.data import json_dumps
from compas.data import json_loads
from compas.tolerance import TOL

from compas_timber.elements import PlateGeometry


def test_plate_geometry_serialization():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)
    pg_copy = json_loads(json_dumps(pg))
    assert all([TOL.is_allclose(pg.outline_a.points[i], pg_copy.outline_a.points[i]) for i in range(len(pg.outline_a.points))]), "copied outline_a does not match"


def test_plate_geometry_serialization_with_opening():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    opening = Polyline([Point(2, 2, 0), Point(2, 5, 0), Point(5, 5, 0), Point(5, 2, 0), Point(2, 2, 0)])
    pg = PlateGeometry(polyline_a, polyline_b, openings=[opening])
    pg_copy = json_loads(json_dumps(pg))
    assert all([TOL.is_allclose(opening.points[i], pg_copy.openings[0].points[i]) for i in range(len(opening.points))]), "copied outline_a does not match"


def test_set_extension_plane():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]
    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    plane_copies = [plane.copy() for plane in pg.edge_planes.values()]
    assert all([TOL.is_allclose(planes[i].normal, plane_copies[i].normal) for i in range(0, 3)])
    assert TOL.is_allclose(plane.normal, plane_copies[3].normal)
    assert not TOL.is_allclose(planes[3].normal, plane_copies[3].normal)


def test_apply_and_remove_exensions():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    extended_polyline_b = Polyline([Point(0, -1, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, -1, 1), Point(0, -1, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]

    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    pg.apply_edge_extensions()
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(polyline_b))])
    pg.remove_blank_extension()
    assert all([TOL.is_allclose(pg.outline_b[i], polyline_b[i]) for i in range(len(polyline_b))])
    for i in range(len(planes)):
        assert TOL.is_allclose(planes[i].normal, list(pg.edge_planes.values())[i].normal)


def test_apply_and_remove_exensions_with_index():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    extended_polyline_b = Polyline([Point(0, -1, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, -1, 1), Point(0, -1, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)
    planes = [plane.copy() for plane in pg.edge_planes.values()]
    plane = Plane([0, 0, 0], [0, -1, -1])
    pg.set_extension_plane(3, plane)
    pg.apply_edge_extensions()
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(extended_polyline_b))])
    pg.remove_blank_extension(2)  # removing extension at index 2 should not affect index 3
    assert TOL.is_allclose(plane.normal, pg.edge_planes[3].normal)
    assert all([TOL.is_allclose(pg.outline_b[i], extended_polyline_b[i]) for i in range(len(extended_polyline_b))])
    pg.remove_blank_extension(3)  # removing extension at index 3 revert to original
    assert all([TOL.is_allclose(planes[i].normal, list(pg.edge_planes.values())[i].normal) for i in range(len(planes))])
    assert all([TOL.is_allclose(pg.outline_b[i], polyline_b[i]) for i in range(len(polyline_b))])

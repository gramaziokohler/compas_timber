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


def test_compute_shape_no_openings(mocker):
    """compute_shape builds polygons from outlines and calls Brep.from_polygons."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)

    mock_brep = mocker.MagicMock()
    mock_from_polygons = mocker.patch("compas_timber.elements.plate_geometry.Brep.from_polygons", return_value=mock_brep)

    result = pg.compute_shape()

    mock_from_polygons.assert_called_once()
    polygons = mock_from_polygons.call_args[0][0]
    # 2 cap polygons + 4 side polygons for a rectangular plate
    assert len(polygons) == 6
    assert result is mock_brep


def test_compute_shape_from_polygons_returns_list(mocker):
    """When Brep.from_polygons returns a single-element list (Rhino quirk), it should be unwrapped."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)

    mock_brep = mocker.MagicMock()
    mocker.patch("compas_timber.elements.plate_geometry.Brep.from_polygons", return_value=[mock_brep])

    result = pg.compute_shape()

    assert result is mock_brep


def test_compute_shape_from_polygons_returns_multiple_breps_raises(mocker):
    """When Brep.from_polygons returns multiple breps, a ValueError should be raised."""
    from pytest import raises

    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)

    mock_brep_1 = mocker.MagicMock()
    mock_brep_2 = mocker.MagicMock()
    mocker.patch("compas_timber.elements.plate_geometry.Brep.from_polygons", return_value=[mock_brep_1, mock_brep_2])

    with raises(ValueError):
        pg.compute_shape()


def test_compute_shape_with_opening(mocker):
    """compute_shape subtracts opening breps from the plate brep."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    opening = Polyline([Point(2, 2, 0), Point(2, 5, 0), Point(5, 5, 0), Point(5, 2, 0), Point(2, 2, 0)])
    pg = PlateGeometry(polyline_a, polyline_b, openings=[opening])

    mock_plate_brep = mocker.MagicMock()
    mock_opening_brep = mocker.MagicMock()
    mocker.patch("compas_timber.elements.plate_geometry.Brep.from_polygons", side_effect=[mock_plate_brep, mock_opening_brep])

    result = pg.compute_shape()

    # opening brep should be subtracted via __isub__
    mock_plate_brep.__isub__.assert_called_once_with(mock_opening_brep)
    assert result is mock_plate_brep.__isub__.return_value


def test_compute_shape_with_unclosed_opening_raises(mocker):
    """An opening polyline that is not closed should raise ValueError."""
    from pytest import raises

    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    # NOT closed: first point != last point
    bad_opening = Polyline([Point(2, 2, 0), Point(2, 5, 0), Point(5, 5, 0), Point(5, 2, 0)])
    pg = PlateGeometry(polyline_a, polyline_b, openings=[bad_opening])

    mock_brep = mocker.MagicMock()
    mocker.patch("compas_timber.elements.plate_geometry.Brep.from_polygons", return_value=mock_brep)

    with raises(ValueError):
        pg.compute_shape()


def test_compute_shape_applies_edge_extensions(mocker):
    """compute_shape should apply edge extensions before building geometry."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)

    mock_apply = mocker.patch.object(pg, "apply_edge_extensions")
    mock_brep = mocker.MagicMock()
    mocker.patch("compas_timber.elements.plate_geometry.Brep.from_polygons", return_value=mock_brep)

    pg.compute_shape()

    mock_apply.assert_called_once()

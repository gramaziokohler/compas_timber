import pytest
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
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


@pytest.mark.requires_occ
def test_compute_shape_no_openings():
    """compute_shape builds a closed solid with one face per polygon (2 caps + 4 sides for a rectangular plate)."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)

    brep = pg.compute_shape()

    assert len(brep.faces) == 6
    assert brep.is_solid
    assert brep.is_closed


@pytest.mark.requires_occ
def test_compute_shape_applies_edge_extensions():
    """compute_shape should apply edge extensions before building geometry."""
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = PlateGeometry(polyline_a, polyline_b)
    unextended_volume = pg.compute_shape().volume

    pg.set_extension_plane(3, Plane([0, 0, 0], [0, -1, -1]))
    extended_brep = pg.compute_shape()

    # the extension enlarges outline_b, so if apply_edge_extensions ran, the solid must be bigger
    assert extended_brep.volume > unextended_volume
    assert extended_brep.is_solid
    assert extended_brep.is_closed


@pytest.mark.requires_occ
def test_compute_shape_produces_solid_with_correct_volume():
    """compute_shape should produce a closed solid with the expected volume (OCC backend).

    Regression test: the old side-polygon point order
    [outline_a[i], outline_a[i+1], outline_b[i+1], outline_b[i]]
    produced an inside-out solid on some backends. The corrected order
    [outline_a[i], outline_b[i], outline_b[i+1], outline_a[i+1]]
    ensures outward-facing normals and a valid solid.

    Note: this test exercises the real OCC Brep backend without mocking.
    On the OCC backend the volume property returns abs(mass), so a negative raw
    volume (inside-out solid) is masked.  The is_solid / is_closed assertions
    additionally guard against the sewing step silently failing to produce a
    proper solid.
    """
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 5, 0), Point(0, 5, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 5, 1), Point(0, 5, 1), Point(0, 0, 1)])
    pg = PlateGeometry(outline_a, outline_b)

    brep = pg.compute_shape()

    expected_volume = 10 * 5 * 1  # length * width * thickness
    assert TOL.is_close(brep.volume, expected_volume)
    assert brep.is_solid
    assert brep.is_closed


def test_from_global_outlines_orientation_sets_local_yaxis():
    """When `orientation` is given, the local frame's y-axis should follow it, regardless of outline_b's side."""
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 5, 0), Point(0, 5, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(p[0], p[1], p[2] + 1) for p in outline_a.points])  # offset in +Z
    orientation = Vector(0, 1, 0)

    pg = PlateGeometry.from_global_outlines(outline_a, outline_b, orientation=orientation)

    # frame.yaxis must be parallel to the requested orientation vector
    assert TOL.is_allclose(cross_vectors(pg.frame.yaxis, orientation), [0, 0, 0])


def test_from_global_outlines_orientation_forces_rotation():
    """`orientation` should rotate the local outline to align local +Y with it, even when that
    differs from the frame the algorithm would otherwise derive from the outline geometry.

    Uses an asymmetric outline (no two edges the same length, no symmetry) so that a wrong
    rotation angle, a mirrored outline, or a mismatch between the returned frame and the actual
    local outline can't accidentally satisfy the checks below.
    """
    outline_a = Polyline([Point(0, 0, 0), Point(8, 0, 0), Point(6, 4, 0), Point(1, 5, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(p[0], p[1], p[2] + 1) for p in outline_a.points])
    orientation = Vector(1, 1, 0)  # 45 degrees, not aligned with any edge of outline_a

    pg_default = PlateGeometry.from_global_outlines(outline_a, outline_b)
    pg_oriented = PlateGeometry.from_global_outlines(outline_a, outline_b, orientation=orientation)

    # orientation actually changed the frame - not coincidentally the same as the default one
    assert not TOL.is_allclose(cross_vectors(pg_default.frame.yaxis, pg_oriented.frame.yaxis), [0, 0, 0])

    # the oriented frame's y-axis follows the requested orientation vector
    assert TOL.is_allclose(cross_vectors(pg_oriented.frame.yaxis, orientation), [0, 0, 0])

    # mapping the local (rotated) outline back through the returned frame must exactly reproduce
    # the original, asymmetric global outline - this only holds if the rotation embedded in the
    # frame matches the rotation actually applied to the outline points.
    for local_pt, global_pt in zip(pg_oriented.outline_a.points, outline_a.points):
        assert TOL.is_allclose(pg_oriented.frame.to_world_coordinates(local_pt), global_pt)


def test_from_global_outlines_orientation_consistent_when_outline_b_flipped():
    """The frame's relationship to `orientation` should not depend on which side outline_b is offset to.

    Regression test: an earlier implementation swapped the x/y axes when flipping the frame to
    account for outline_b lying in -Z space, which discarded the orientation constraint for the
    flipped case. The fix negates the x-axis instead, keeping the y-axis aligned with `orientation`.
    """
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 5, 0), Point(0, 5, 0), Point(0, 0, 0)])
    outline_b_pos = Polyline([Point(p[0], p[1], p[2] + 1) for p in outline_a.points])  # +Z, no flip needed
    outline_b_neg = Polyline([Point(p[0], p[1], p[2] - 1) for p in outline_a.points])  # -Z, triggers frame flip
    orientation = Vector(0, 1, 0)

    pg_pos = PlateGeometry.from_global_outlines(outline_a, outline_b_pos, orientation=orientation)
    pg_neg = PlateGeometry.from_global_outlines(outline_a, outline_b_neg, orientation=orientation)

    # y-axis stays parallel to orientation in both the flipped and non-flipped case
    assert TOL.is_allclose(cross_vectors(pg_pos.frame.yaxis, orientation), [0, 0, 0])
    assert TOL.is_allclose(cross_vectors(pg_neg.frame.yaxis, orientation), [0, 0, 0])

    # and its relationship (same vs. opposite direction) to orientation is consistent between the two cases
    assert TOL.is_close(dot_vectors(pg_pos.frame.yaxis, orientation), dot_vectors(pg_neg.frame.yaxis, orientation))

    # regardless of which side outline_b was offset to, local outline_b always ends up at +thickness
    assert all(TOL.is_close(p[2], pg_pos.thickness) for p in pg_pos.outline_b.points)
    assert all(TOL.is_close(p[2], pg_neg.thickness) for p in pg_neg.outline_b.points)

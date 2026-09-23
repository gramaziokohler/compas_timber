import pytest

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.elements import Panel
from compas_timber.panel_features.opening import Opening
from compas_timber.panel_features.opening import OpeningType


@pytest.fixture
def flat_panel():
    outline = Polyline([Point(0, 0, 0), Point(4, 0, 0), Point(4, 3, 0), Point(0, 3, 0), Point(0, 0, 0)])
    return Panel.from_outline_thickness(outline, 0.2)


@pytest.fixture
def simple_opening_outlines():
    outline_a = Polyline([Point(1, 1, 0), Point(2, 1, 0), Point(2, 2, 0), Point(1, 2, 0), Point(1, 1, 0)])
    outline_b = Polyline([Point(1, 1, 0.2), Point(2, 1, 0.2), Point(2, 2, 0.2), Point(1, 2, 0.2), Point(1, 1, 0.2)])
    return outline_a, outline_b


# ==========================================================================
# OpeningType tests
# ==========================================================================


def test_opening_type_is_str():
    assert isinstance(OpeningType.DOOR, str)
    assert isinstance(OpeningType.WINDOW, str)


def test_opening_type_members_exist():
    assert "DOOR" in OpeningType.__members__
    assert "WINDOW" in OpeningType.__members__


def test_opening_type_members_distinct():
    assert OpeningType.DOOR != OpeningType.WINDOW


# ==========================================================================
# Opening instantiation tests
# ==========================================================================


def test_opening_init(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    frame = Frame.worldXY()
    opening = Opening(frame, outline_a, outline_b)
    assert opening is not None
    assert opening.opening_type == OpeningType.WINDOW


def test_opening_init_default_type(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    opening = Opening(Frame.worldXY(), outline_a, outline_b)
    assert opening.opening_type == OpeningType.WINDOW


def test_opening_init_door_type(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    opening = Opening(Frame.worldXY(), outline_a, outline_b, opening_type=OpeningType.DOOR)
    assert opening.opening_type == OpeningType.DOOR


def test_opening_name(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    opening = Opening(Frame.worldXY(), outline_a, outline_b, name="MyOpening")
    assert opening.name == "MyOpening"


# ==========================================================================
# Opening outline properties
# ==========================================================================


def test_opening_outlines_at_worldxy(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    opening = Opening(Frame.worldXY(), outline_a, outline_b)
    # At worldXY frame, transformation is identity so outlines match originals
    for pt_orig, pt_prop in zip(outline_a.points, opening.outline_a.points):
        assert TOL.is_allclose(pt_orig, pt_prop)
    for pt_orig, pt_prop in zip(outline_b.points, opening.outline_b.points):
        assert TOL.is_allclose(pt_orig, pt_prop)


def test_opening_outlines_with_transformation(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    frame = Frame(Point(0, 0, 1), Vector(1, 0, 0), Vector(0, 1, 0))
    opening = Opening(frame, outline_a, outline_b)
    # outline_a property applies self.transformation (from frame)
    # The frame elevates by 1 in z, so all points should be shifted
    expected_z = outline_a.points[0][2] + 1
    for pt in opening.outline_a.points:
        assert TOL.is_close(pt[2], expected_z)


# ==========================================================================
# Opening serialization (__data__)
# ==========================================================================


def test_opening_data_has_required_keys(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    opening = Opening(Frame.worldXY(), outline_a, outline_b)
    data = opening.__data__
    assert "outline_a" in data
    assert "outline_b" in data
    assert "opening_type" in data


def test_opening_data_opening_type(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    opening = Opening(Frame.worldXY(), outline_a, outline_b, opening_type=OpeningType.DOOR)
    assert opening.__data__["opening_type"] == OpeningType.DOOR


def test_opening_data_stores_local_outlines(simple_opening_outlines):
    outline_a, outline_b = simple_opening_outlines
    frame = Frame(Point(5, 5, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    opening = Opening(frame, outline_a, outline_b)
    # __data__ stores the local (untransformed) outlines, not the world-space ones
    data_outline_a = opening.__data__["outline_a"]
    for pt_orig, pt_data in zip(outline_a.points, data_outline_a.points):
        assert TOL.is_allclose(pt_orig, pt_data)


# ==========================================================================
# Opening.from_outline_panel tests
# ==========================================================================


def test_from_outline_panel_returns_opening(flat_panel):
    outline = Polyline([Point(1, 1, 0.1), Point(2, 1, 0.1), Point(2, 2, 0.1), Point(1, 2, 0.1), Point(1, 1, 0.1)])
    opening = Opening.from_outline_panel(outline, flat_panel)
    assert isinstance(opening, Opening)


def test_from_outline_panel_default_type(flat_panel):
    outline = Polyline([Point(1, 1, 0.1), Point(2, 1, 0.1), Point(2, 2, 0.1), Point(1, 2, 0.1), Point(1, 1, 0.1)])
    opening = Opening.from_outline_panel(outline, flat_panel)
    assert opening.opening_type == OpeningType.WINDOW


def test_from_outline_panel_door_type(flat_panel):
    outline = Polyline([Point(1, 1, 0.1), Point(2, 1, 0.1), Point(2, 2, 0.1), Point(1, 2, 0.1), Point(1, 1, 0.1)])
    opening = Opening.from_outline_panel(outline, flat_panel, opening_type=OpeningType.DOOR)
    assert opening.opening_type == OpeningType.DOOR


def test_from_outline_panel_outlines_differ_by_thickness(flat_panel):
    outline = Polyline([Point(1, 1, 0.1), Point(2, 1, 0.1), Point(2, 2, 0.1), Point(1, 2, 0.1), Point(1, 1, 0.1)])
    opening = Opening.from_outline_panel(outline, flat_panel)
    # world-space outline_a and outline_b should differ by panel.thickness in z
    for pt_a, pt_b in zip(opening.outline_a.points, opening.outline_b.points):
        assert TOL.is_close(abs(pt_b[2] - pt_a[2]), flat_panel.thickness)

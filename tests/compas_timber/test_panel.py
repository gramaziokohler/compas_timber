import pytest

from compas.data import json_dumps, json_loads

from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Plane
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.elements import Panel
from compas_timber.elements import Beam
from compas_timber.elements.panel import extract_door_openings
from compas_timber.model import TimberModel

from brep_mocks import make_plate_brep
from brep_mocks import make_single_face_brep


@pytest.fixture
def model():
    """Create a basic TimberModel with two panels."""

    model = TimberModel()

    # Create two panels
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 10, 0), Point(10, 10, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1, name="Best Panel")
    panel_b = Panel.from_outline_thickness(polyline_b, 1, name="Second Best Panel")

    model.add_element(panel_a)
    model.add_element(panel_b)

    return model


def test_flat_panel_creation():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [([0, 0, 0], [-1, 0, 0]), ([0, 20, 0], [0, 1, 0]), ([10, 20, 0], [1, 0, 0]), ([10, 0, 0], [0, -1, 0])]
    assert all([panel_a.outline_a.points[i] == polyline_a.points[i] for i in range(len(panel_a.outline_a.points))]), "Expected panel to match input polyline"
    assert panel_a.thickness == 1, "Expected panel thickness to match input thickness"
    assert panel_a.length == 10, "Expected panel length to be 10"
    assert panel_a.width == 20, "Expected panel width to be 20"
    assert TOL.is_allclose(panel_a.normal, [0, 0, 1]), "Expected the normal to be the world Z-axis"
    for expected, plane in zip(expected_edge_planes, panel_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    for obb_pt, expected_pt in zip(panel_a.obb.points, Box.from_points([Point(0, 0, 0), Point(10, 20, 1)]).points):
        assert TOL.is_allclose(obb_pt, expected_pt)


def test_sloped_panel_creation():
    polyline_a = Polyline([Point(0, 10, 0), Point(10, 10, 0), Point(20, 20, 10), Point(0, 20, 10), Point(0, 10, 0)])
    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    expected_edge_planes = [
        ([0, 10, 0], [0, -0.707106781, -0.707106781]),
        ([10, 10, 0], [0.81649658, -0.40824829, -0.40824829]),
        ([20, 20, 10], [0, 0.707106781, 0.707106781]),
        ([0, 20, 10], [-1, 0, 0]),
    ]

    expected_obb = Box(
        xsize=14.142135623730951,
        ysize=20.0,
        zsize=1.0,
        frame=Frame(
            point=Point(x=10.0, y=15.353553390593273, z=4.646446609406729), xaxis=Vector(x=0.0, y=0.7071067811865475, z=0.7071067811865476), yaxis=Vector(x=1.0, y=0.0, z=0.0)
        ),
    )

    assert panel_a.frame.point == Point(0, 10, 0), "Expected panel frame to match input polyline"
    assert all([TOL.is_allclose(panel_a.outline_a.points[i], polyline_a.points[i]) for i in range(len(panel_a.outline_a.points))]), "Expected panel to match input polyline"
    assert TOL.is_close(panel_a.thickness, 1), "Expected panel thickness to match input thickness"
    assert TOL.is_close(panel_a.length, 14.1421356237), "Expected panel length to be 10*sqrt(2)"
    assert TOL.is_close(panel_a.width, 20), "Expected panel width to be 20"
    assert TOL.is_allclose(panel_a.normal, [0, 0.707106781, -0.707106781]), "Expected the normal to be at 45 degrees"
    for expected, plane in zip(expected_edge_planes, panel_a.edge_planes.values()):
        assert TOL.is_allclose(expected[0], plane[0])
        assert TOL.is_allclose(expected[1], plane[1])
    assert TOL.is_allclose(expected_obb.frame.point, panel_a.obb.frame.point)
    assert TOL.is_allclose(expected_obb.frame.xaxis, panel_a.obb.frame.xaxis)
    assert TOL.is_allclose(expected_obb.frame.yaxis, panel_a.obb.frame.yaxis)
    assert TOL.is_close(expected_obb.xsize, panel_a.obb.xsize)
    assert TOL.is_close(expected_obb.ysize, panel_a.obb.ysize)
    assert TOL.is_close(panel_a.obb.zsize, 1.0)


def test_panel_addition_to_model(model):
    panels = model.panels
    assert panels[0].modeltransformation == panels[0].transformation, "Expected panel model transformation to match panel transformation"
    assert panels[1].modeltransformation == panels[1].transformation, "Expected panel model transformation to match panel transformation"
    assert len(list(model.elements())) == 2, "Expected model to contain two panels"
    assert all(isinstance(element, Panel) for element in model.elements()), "Expected all elements in the model to be panels"


def test_add_beam_to_panel(model):
    beam = Beam(Frame.worldXY(), length=5, width=0.3, height=0.5, name="Beam 1")
    model.add_element(beam, parent=model.panels[1])
    assert len(list(model.elements())) == 3, "Expected model to contain two panels"
    assert beam in model.panels[1].children, "Expected beam to be a child of the panel"
    assert beam.modeltransformation == model.panels[1].transformation, "Expected beam model transformation to match panel transformation"


def test_copy_panel_model(model):
    model_copy = json_loads(json_dumps(model))

    assert len(list(model_copy.elements())) == len(list(model.elements())), "Expected copied model to have same number of elements"

    for original, copy in zip(model.panels, model_copy.panels):
        assert isinstance(copy, Panel)
        assert TOL.is_close(original.thickness, copy.thickness)
        assert original.frame == copy.frame
        assert TOL.is_close(original.width, copy.width)
        assert TOL.is_close(original.length, copy.length)
        assert original.name == copy.name


def test_panel_serialization_with_attributes_kwargs():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1, custom_attribute="custom_value", another_attribute=42)

    deserialized = json_loads(json_dumps(panel_a))

    assert deserialized.thickness == 1
    assert deserialized.length == 10
    assert deserialized.width == 20
    assert deserialized.attributes["custom_attribute"] == "custom_value"
    assert deserialized.attributes["another_attribute"] == 42


def test_panel_serialization_with_attributes():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])

    panel_a = Panel.from_outline_thickness(polyline_a, 1)
    panel_a.attributes["custom_attribute"] = "custom_value"
    panel_a.attributes["another_attribute"] = 42

    deserialized = json_loads(json_dumps(panel_a))

    assert deserialized.thickness == 1
    assert deserialized.length == 10
    assert deserialized.width == 20
    assert deserialized.attributes["custom_attribute"] == "custom_value"
    assert deserialized.attributes["another_attribute"] == 42


def test_from_outline_thickness():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    panel_a = Panel.from_outlines(polyline_a, polyline_b)
    panel_b = Panel.from_outline_thickness(polyline_a, 1)

    for pt_a, pt_b in zip(panel_a.outline_b, panel_b.outline_b):
        assert TOL.is_allclose(pt_a, pt_b)


def test_set_extension_plane():
    polyline_a = Polyline([Point(0, 0, 0), Point(0, 20, 0), Point(10, 20, 0), Point(10, 0, 0), Point(0, 0, 0)])
    polyline_b = Polyline([Point(0, 0, 1), Point(0, 20, 1), Point(10, 20, 1), Point(10, 0, 1), Point(0, 0, 1)])
    pg = Panel.from_outlines(polyline_a, polyline_b)
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
    pg = Panel.from_outlines(polyline_a, polyline_b)
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
    pg = Panel.from_outlines(polyline_a, polyline_b)
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


def test_panel_geometry_triggers_model_geometry_calculation(mocker):
    panel = Panel(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=10, length=20, thickness=1)

    mock_geometry = mocker.MagicMock()
    mock_compute = mocker.MagicMock(return_value=mock_geometry)
    mocker.patch("compas_timber.elements.Panel.compute_modelgeometry", side_effect=mock_compute)

    geometry = panel.geometry

    mock_compute.assert_called_once()
    assert geometry is mock_geometry


def test_panel_geometry_cannot_be_manually_set(mocker):
    panel = Panel(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=10, length=20, thickness=1)

    with pytest.raises(AttributeError):
        panel.geometry = mocker.MagicMock()


def test_from_face_thickness_rectangular():
    pts = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    brep = make_single_face_brep(pts)
    thickness = 1.0
    panel = Panel.from_face_thickness(brep, thickness)

    assert panel is not None
    assert TOL.is_close(panel.thickness, thickness)
    assert panel.outline_a is not None
    assert panel.outline_b is not None
    assert len(panel.outline_a.points) == 5
    assert len(panel.outline_b.points) == 5

    for pt_a, pt_b in zip(panel.outline_a.points, panel.outline_b.points):
        assert TOL.is_close(pt_a.distance_to_point(pt_b), thickness)


def test_from_face_thickness_with_custom_vector():
    pts = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    brep = make_single_face_brep(pts)
    thickness = 1.0
    vector = Vector(0, 0, -1)
    panel = Panel.from_face_thickness(brep, thickness, vector=vector)

    assert panel is not None
    assert TOL.is_close(panel.thickness, thickness)
    assert TOL.is_allclose(panel.normal, [0, 0, -1])


def test_from_face_thickness_raises_on_multi_face_brep():
    pts_a = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    pts_b = [Point(0, 0, 1), Point(10, 0, 1), Point(10, 20, 1), Point(0, 20, 1)]
    multi_face_brep = make_plate_brep(pts_a, pts_b)

    with pytest.raises(ValueError):
        Panel.from_face_thickness(multi_face_brep, 1.0)


def test_from_brep_rectangular_box():
    thickness = 1.0
    pts_a = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]
    pts_b = [Point(0, 0, thickness), Point(10, 0, thickness), Point(10, 20, thickness), Point(0, 20, thickness)]
    brep = make_plate_brep(pts_a, pts_b)

    panel = Panel.from_brep(brep)

    assert panel is not None
    assert TOL.is_close(panel.thickness, thickness, atol=0.01)
    assert panel.outline_a is not None
    assert panel.outline_b is not None
    assert len(panel.outline_a.points) == 5
    assert len(panel.outline_b.points) == 5
    assert TOL.is_close(panel.length, 10.0, atol=0.5)
    assert TOL.is_close(panel.width, 20.0, atol=0.5)


def test_from_brep_octagonal_prism():
    import math

    radius = 10.0
    thickness = 2.0
    n_sides = 8

    pts_a = [Point(radius * math.cos(2 * math.pi * i / n_sides), radius * math.sin(2 * math.pi * i / n_sides), 0) for i in range(n_sides)]
    pts_b = [Point(pt.x, pt.y, thickness) for pt in pts_a]
    brep = make_plate_brep(pts_a, pts_b)

    panel = Panel.from_brep(brep)

    assert panel is not None
    assert TOL.is_close(panel.thickness, thickness, atol=0.1)
    assert len(panel.outline_a.points) == n_sides + 1
    assert len(panel.outline_b.points) == n_sides + 1


def test_from_brep_tilted_box():
    import math

    angle = math.pi / 4
    thickness = 1.0
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    base = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 20, 0), Point(0, 20, 0)]

    pts_a = [Point(pt.x, pt.y * cos_a, pt.y * sin_a) for pt in base]
    normal_scaled = Vector(0, -sin_a, cos_a) * thickness
    pts_b = [Point(pt.x + normal_scaled.x, pt.y + normal_scaled.y, pt.z + normal_scaled.z) for pt in pts_a]
    brep = make_plate_brep(pts_a, pts_b)

    panel = Panel.from_brep(brep)

    assert panel is not None
    assert panel.outline_a is not None
    assert panel.outline_b is not None
    assert len(panel.outline_a.points) == len(panel.outline_b.points)


# Wall: 10 wide, 8 tall. Door cutout: x=3..7, height=5.
#
#  (0,8)────────────────(10,8)
#    |                      |
#    |    (3,5)───(7,5)      |
#    |    |           |      |
#  (0,0)─(3,0)   (7,0)─(10,0)
_WALL_WITH_DOOR_A = Polyline([Point(0, 0, 0), Point(3, 0, 0), Point(3, 5, 0), Point(7, 5, 0), Point(7, 0, 0), Point(10, 0, 0), Point(10, 8, 0), Point(0, 8, 0), Point(0, 0, 0)])
_WALL_WITH_DOOR_B = Polyline([Point(0, 0, 1), Point(3, 0, 1), Point(3, 5, 1), Point(7, 5, 1), Point(7, 0, 1), Point(10, 0, 1), Point(10, 8, 1), Point(0, 8, 1), Point(0, 0, 1)])


def test_extract_door_openings_no_door():
    outline_a = Polyline([Point(0, 0, 0), Point(10, 0, 0), Point(10, 8, 0), Point(0, 8, 0), Point(0, 0, 0)])
    outline_b = Polyline([Point(0, 0, 1), Point(10, 0, 1), Point(10, 8, 1), Point(0, 8, 1), Point(0, 0, 1)])
    _, _, openings = extract_door_openings(outline_a, outline_b)
    assert openings == []


def test_extract_door_openings_single_door():
    result_a, result_b, openings = extract_door_openings(_WALL_WITH_DOOR_A.copy(), _WALL_WITH_DOOR_B.copy())
    assert len(openings) == 1
    assert len(result_a.points) == 5  # door removed, simple rectangle remains
    assert len(result_b.points) == 5


def test_extract_door_openings_mismatched_interior_indices_no_error():
    # outline_b has the door notch at a different segment index (extra split before the notch)
    # so interior_indices_a != interior_indices_b — previously this raised ValueError
    outline_a = _WALL_WITH_DOOR_A.copy()  # interior indices: {1, 2, 3}
    outline_b = Polyline(  # shifted point by one place in list door to interior indices: {2, 3, 4}
        [Point(0, 8, 1), Point(0, 0, 1), Point(3, 0, 1), Point(3, 5, 1), Point(7, 5, 1), Point(7, 0, 1), Point(10, 0, 1), Point(10, 8, 1), Point(0, 8, 1)]
    )
    # must not raise; directions don't match so no door is generated
    _, _, openings = extract_door_openings(outline_a, outline_b)
    assert openings == []
